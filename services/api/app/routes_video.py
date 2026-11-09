"""Campaign video analysis with tenant-scoped report history."""

from asyncio import timeout
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from .models import Record
from .security import current_user, db_session, editor, member
from .video import InvalidVideo, MAX_VIDEO_BYTES, extract_video
from .workflow import audit, context, create, get_record, public
from marketing_ai.video_review import review_video, video_model_available

router = APIRouter(prefix="/api/workspaces/{workspace_id}", dependencies=[Depends(member)])
_analysis_slot = BoundedSemaphore(1)


def _analyze(path, snapshot):
    duration, frames, transcript, has_audio = extract_video(path)
    review = review_video(snapshot, duration, frames, transcript)
    return {
        **review,
        "duration_ms": duration,
        "sample_times_ms": [timestamp for timestamp, _ in frames],
        "transcript": transcript,
        "has_audio": has_audio,
    }


@router.get("/campaigns/{campaign_id}/video-analyses")
def video_analyses(workspace_id: str, campaign_id: str, db=Depends(db_session)):
    get_record(db, workspace_id, "campaign", campaign_id)
    query = select(Record).where(
        Record.workspace_id == workspace_id,
        Record.kind == "video_analysis",
        Record.parent_id == campaign_id,
    ).order_by(Record.created_at.desc(), Record.id.desc()).limit(10)
    return {"available": video_model_available(), "items": [public(row) for row in db.scalars(query)]}


@router.post("/campaigns/{campaign_id}/video-analyses", status_code=201,
             dependencies=[Depends(editor)])
async def analyze_video(
    workspace_id: str,
    campaign_id: str,
    request: Request,
    x_video_filename: str = Header(min_length=1, max_length=2160),
    consent: bool = False,
    db=Depends(db_session),
    user=Depends(current_user),
):
    campaign = get_record(db, workspace_id, "campaign", campaign_id)
    if not consent:
        raise HTTPException(422, "请确认有权分析该视频，并同意把关键画面和转写交给 DeepSeek")
    try:
        name = Path(unquote(x_video_filename, errors="strict").replace("\\", "/")).name
    except UnicodeError:
        raise HTTPException(422, "视频文件名无效") from None
    if not name or len(name) > 240 or any(ord(char) < 32 for char in name):
        raise HTTPException(422, "视频文件名无效")
    suffix = Path(name).suffix.lower()
    if suffix not in (".mp4", ".mov"):
        raise HTTPException(422, "请选择 MP4 或 MOV 视频")
    if not video_model_available():
        raise HTTPException(503, "视频分析需要启用 DeepSeek 官方模型")
    if not _analysis_slot.acquire(blocking=False):
        raise HTTPException(429, "正在分析另一个视频，请稍后重试")
    try:
        request.app.state.limiter.check(("video-analysis", workspace_id), limit=8, window=3600)
        snapshot = context(db, workspace_id, campaign)
        # Avoid holding a read transaction while uploading and analyzing the video.
        db.rollback()
        with TemporaryDirectory(prefix="heritage-video-") as temp:
            path = Path(temp) / ("upload" + suffix)
            size = 0
            async with timeout(90):
                with path.open("wb") as target:
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > MAX_VIDEO_BYTES:
                            raise HTTPException(413, "视频文件不得超过 40 MiB")
                        target.write(chunk)
            if not size:
                raise HTTPException(422, "请选择非空视频")
            result = await run_in_threadpool(_analyze, path, snapshot)
        report = create(db, workspace_id, "video_analysis", {"filename": name, **result}, parent=campaign_id)
        audit(db, workspace_id, user, "analyze_video", report)
        return public(report)
    except InvalidVideo as error:
        raise HTTPException(422, str(error)) from None
    except TimeoutError:
        raise HTTPException(408, "视频上传超时，请压缩后重试") from None
    except RuntimeError as error:
        raise HTTPException(502, str(error)) from None
    finally:
        _analysis_slot.release()
