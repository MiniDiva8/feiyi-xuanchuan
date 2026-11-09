import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import av
import pytest
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/marketing-ai")]


def make_video(path, *, audio=False, seconds=2):
    with av.open(str(path), "w") as output:
        video = output.add_stream("mpeg4", rate=8)
        video.width = 160
        video.height = 96
        video.pix_fmt = "yuv420p"
        if audio:
            sound = output.add_stream("aac", rate=16000)
            sound.layout = "mono"
        for index in range(8 * seconds):
            image = Image.new("RGB", (160, 96), (index % 256, 80, 130))
            for packet in video.encode(av.VideoFrame.from_image(image)):
                output.mux(packet)
        for packet in video.encode():
            output.mux(packet)
        if audio:
            for _ in range(16 * seconds):
                frame = av.AudioFrame(format="s16", layout="mono", samples=1000)
                frame.sample_rate = 16000
                frame.planes[0].update(bytes(frame.planes[0].buffer_size))
                for packet in sound.encode(frame):
                    output.mux(packet)
            for packet in sound.encode():
                output.mux(packet)
    return path


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    db = "sqlite:///" + str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_URL", db)
    monkeypatch.setenv("MARKETING_AI_API_KEY", "stub-key")
    monkeypatch.setenv("MARKETING_AI_MODEL", "deepseek-flash")
    monkeypatch.setenv("MARKETING_AI_BASE_URL", "https://api.deepseek.com")
    from app.main import create_app

    app = create_app(db)
    with TestClient(app) as client:
        owner = register(client, "one")
        base = f"/api/workspaces/{owner}"
        activity = client.post(base + "/campaigns", json={
            "name": "蓝染展示", "objective": "awareness", "audience": "访客",
            "start_date": "2026-11-10", "end_date": "2026-11-16", "budget": 100,
            "channels": ["抖音"],
        })
        assert activity.status_code == 201
        yield client, app, f"{base}/campaigns/{activity.json()['id']}/video-analyses"


def register(client, label):
    response = client.post("/api/auth/register", json={
        "name": label, "workspace_name": label, "email": f"{label}@qa.invalid",
        "password": "Video-Test-2026!",
    })
    assert response.status_code == 201
    return response.json()["workspaces"][0]["id"]


def provider(result):
    class Response(io.BytesIO):
        status = 200

    return Response(json.dumps({
        "choices": [{"message": {"content": json.dumps(result, ensure_ascii=False)}}],
        "usage": {"total_tokens": 10},
    }).encode())


def upload(client, endpoint, content, name="蓝染.mp4", consent=True):
    return client.post(
        endpoint + ("?consent=true" if consent else ""),
        headers={"X-Video-Filename": quote(name), "Content-Type": "application/octet-stream"},
        content=content,
    )


def test_video_upload_uses_actual_frames_and_saves_report(workspace, tmp_path, monkeypatch):
    from marketing_ai import engine

    client, app, endpoint = workspace
    raw = make_video(tmp_path / "clip.mp4").read_bytes()
    calls = []

    def transport(request, timeout):
        calls.append(request.full_url)
        body = json.loads(request.data)
        parts = body["messages"][1]["content"]
        assert any(part["type"] == "image_url" and part["image_url"]["url"].startswith(
            "data:image/jpeg;base64,"
        ) for part in parts)
        return provider({
            "summary": "采样画面基本一致",
            "suggestions": [{
                "kind": "hook", "start_ms": 0, "end_ms": 1000,
                "evidence": "开头是静态画面", "suggestion": "先展示工序",
            }],
            "limitations": ["没有音轨，需人工核对字幕"],
        })

    monkeypatch.setattr(engine, "_open", transport)
    response = upload(client, endpoint, raw)
    assert response.status_code == 201, response.text
    report = response.json()
    assert report["filename"] == "蓝染.mp4"
    assert report["duration_ms"] == 2000
    assert report["sample_times_ms"][0] == 0
    assert report["transcript"] == []
    assert report["has_audio"] is False
    assert report["suggestions"][0]["end_ms"] == 1000
    assert client.get(endpoint).json() == {"available": True, "items": [report]}
    assert calls == ["https://api.deepseek.com/chat/completions"]
    from app.models import Record
    with app.state.sessions() as db:
        assert db.get(Record, report["id"]).blob is None
    with TestClient(app) as outsider:
        register(outsider, "two")
        assert outsider.get(endpoint).status_code == 404
        assert upload(outsider, endpoint, raw).status_code == 404


def test_video_rejects_bad_inputs_and_malformed_provider(workspace, tmp_path, monkeypatch):
    from marketing_ai import engine

    client, _, endpoint = workspace
    assert upload(client, endpoint, b"some data", consent=False).status_code == 422
    assert upload(client, endpoint, b"some data", "clip.avi").status_code == 422
    assert upload(client, endpoint, b"not a video").status_code == 422
    assert upload(client, endpoint, b"").status_code == 422
    oversized = client.post(endpoint + "?consent=true", headers={
        "X-Video-Filename": "test.mp4", "Content-Length": str(40 * 1024 * 1024 + 1),
    })
    assert oversized.status_code == 413
    monkeypatch.setattr(engine, "_open", lambda *_: provider({
        "summary": "summary", "limitations": [],
        "suggestions": [{"kind": "cut", "start_ms": 3000, "end_ms": 5000,
                         "evidence": "fake", "suggestion": "fake"}],
    }))
    assert upload(client, endpoint, make_video(tmp_path / "clip.mp4").read_bytes()).status_code == 502
    assert client.get(endpoint).json()["items"] == []
    monkeypatch.setenv("MARKETING_AI_BASE_URL", "https://other.example")
    assert client.get(endpoint).json()["available"] is False
    assert upload(client, endpoint, b"some data").status_code == 503


def test_audio_track_is_extracted_and_transcript_keeps_time(tmp_path, monkeypatch):
    from app import video

    def transcribe(source, **kwargs):
        assert source.ndim == 1
        assert source.dtype.name == "float32"
        assert 30000 <= len(source) <= 35000
        return iter([SimpleNamespace(start=0.2, end=1.0, text="这是蓝染")]), None

    monkeypatch.setattr(video, "_speech_model", lambda: SimpleNamespace(transcribe=transcribe))
    duration, frames, transcript, has_audio = video.extract_video(
        make_video(tmp_path / "audio.mp4", audio=True)
    )
    assert 2000 <= duration < 2200
    assert frames and has_audio
    assert transcript == [{"start_ms": 200, "end_ms": 1000, "text": "这是蓝染"}]
