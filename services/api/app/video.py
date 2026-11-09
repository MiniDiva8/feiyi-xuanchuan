"""Bounded local extraction of frames and speech from short uploads."""

import io
import math
import os
import time
from functools import lru_cache

import av
import numpy as np
from faster_whisper import WhisperModel

MAX_VIDEO_BYTES = 40 * 1024 * 1024
MAX_DURATION_MS = 90_000
_SAMPLE_RATE = 16_000


class InvalidVideo(ValueError):
    pass


def _frames(container, stream, duration, origin, deadline):
    stream.codec_context.thread_count = 2
    samples = sorted({0.0, min(1.0, duration / 2), min(3.0, duration * 0.75)}
                     | {duration * index / 8 for index in range(1, 8)})
    images = {}
    for sample in samples:
        container.seek(int((sample + origin) / stream.time_base), stream=stream)
        for frame in container.decode(stream):
            if time.monotonic() > deadline:
                raise InvalidVideo("视频解码耗时过长，请压缩后重试")
            if frame.time is None:
                continue
            elapsed = frame.time - origin
            if elapsed < sample - 0.015 or elapsed >= duration:
                continue
            timestamp = max(0, round(elapsed * 1000))
            if timestamp not in images:
                image = frame.to_image()
                image.thumbnail((960, 960))
                output = io.BytesIO()
                image.save(output, "JPEG", quality=78)
                images[timestamp] = output.getvalue()
            break
    if not images:
        raise InvalidVideo("未读到视频画面，请导出为可播放的 MP4 或 MOV")
    return sorted(images.items())


def _audio(path, duration_ms, origin, deadline):
    output = bytearray()
    with av.open(str(path), format="mov", options={"enable_drefs": "0"}) as media:
        if not media.streams.audio:
            return None, 0
        stream = media.streams.audio[0]
        if stream.codec_context.channels > 8:
            raise InvalidVideo("视频音轨声道过多，请导出为单声道或立体声")
        resampler = av.AudioResampler(format="s16", layout="mono", rate=_SAMPLE_RATE)
        remaining = duration_ms * _SAMPLE_RATE // 1000
        offset_ms = 0
        for frame in media.decode(stream):
            if time.monotonic() > deadline:
                raise InvalidVideo("视频音轨解码耗时过长，请压缩后重试")
            if not output and frame.time is not None:
                offset_ms = max(0, min(duration_ms, round((frame.time - origin) * 1000)))
            for part in resampler.resample(frame):
                count = min(remaining, part.samples)
                output.extend(bytes(part.planes[0])[: count * 2])
                remaining -= count
            if remaining <= 0:
                break
        if remaining and output:
            for part in resampler.resample(None):
                count = min(remaining, part.samples)
                output.extend(bytes(part.planes[0])[: count * 2])
                remaining -= count
    if not output:
        return None, 0
    return np.frombuffer(output, dtype="<i2").astype(np.float32) / 32768, offset_ms


@lru_cache(maxsize=1)
def _speech_model():
    return WhisperModel(os.getenv("VIDEO_ASR_MODEL", "base"), device="cpu",
                        compute_type="int8", cpu_threads=2, num_workers=1)


def _transcript(audio, offset_ms, duration_ms):
    if audio is None:
        return []
    try:
        segments, _ = _speech_model().transcribe(audio, beam_size=3, vad_filter=True)
        transcript = []
        for segment in segments:
            start = max(0, round(segment.start * 1000) + offset_ms)
            end = min(duration_ms, round(segment.end * 1000) + offset_ms)
            text = segment.text.strip()[:500]
            if text and start < end:
                transcript.append({"start_ms": start, "end_ms": end, "text": text})
            if len(transcript) >= 60:
                break
        return transcript
    except Exception:
        raise RuntimeError("语音转写暂不可用，请检查本地语音模型或稍后重试") from None


def extract_video(path):
    deadline = time.monotonic() + 45
    try:
        with av.open(str(path), format="mov", options={"enable_drefs": "0"}) as media:
            duration = (media.duration or 0) / av.time_base
            if not 0 < duration <= MAX_DURATION_MS / 1000:
                raise InvalidVideo("请选择时长不超过 90 秒的视频")
            if not media.streams.video:
                raise InvalidVideo("文件中没有视频画面")
            stream = media.streams.video[0]
            if max(stream.width, stream.height) > 4096 or stream.width * stream.height > 9_000_000:
                raise InvalidVideo("视频分辨率过高，请压缩至 4K 或以下")
            if not stream.time_base:
                raise InvalidVideo("视频缺少时间信息，请重新导出")
            origin = (media.start_time or 0) / av.time_base
            frames = _frames(media, stream, duration, origin, deadline)
        duration_ms = math.ceil(duration * 1000)
        audio, offset_ms = _audio(path, duration_ms, origin, deadline)
    except InvalidVideo:
        raise
    except (av.error.FFmpegError, OSError, ValueError):
        raise InvalidVideo("无法读取视频，请重新导出为可播放的 MP4 或 MOV") from None
    return duration_ms, frames, _transcript(audio, offset_ms, duration_ms), audio is not None
