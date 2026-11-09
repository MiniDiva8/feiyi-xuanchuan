from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy import select
from .security import db_session, current_user, member, editor
from .schemas import MetricInput, CSVInput
from .models import Record
from .workflow import records, get_record, public, create, audit
from .metrics import analytics, validate_metric, dedupe, preview

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}", dependencies=[Depends(member)]
)


@router.get("/metrics")
def metric_list(
    workspace_id: str, campaign_id: str | None = None, db=Depends(db_session)
):
    if campaign_id:
        get_record(db, workspace_id, "campaign", campaign_id)
    return [
        public(x)
        for x in records(db, workspace_id, "metric")
        if not campaign_id or x.data["campaign_id"] == campaign_id
    ]


@router.post("/metrics", status_code=201, dependencies=[Depends(editor)])
def metric_create(
    workspace_id: str,
    data: MetricInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    payload = data.model_dump(mode="json")
    validate_metric(db, workspace_id, payload)
    key = dedupe(payload)
    if db.scalar(
        select(Record).where(
            Record.workspace_id == workspace_id,
            Record.kind == "metric",
            Record.dedupe_key == key,
        )
    ):
        raise HTTPException(409, "该数据记录已存在")
    entity = create(db, workspace_id, "metric", payload, dedupe=key)
    audit(db, workspace_id, user, "create", entity)
    return public(entity)


@router.post("/metrics/preview", dependencies=[Depends(editor)])
def csv_preview(workspace_id: str, data: CSVInput, db=Depends(db_session)):
    return preview(db, workspace_id, data.csv)


@router.post("/metrics/import", dependencies=[Depends(editor)])
def csv_import(
    workspace_id: str,
    data: CSVInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    result = preview(db, workspace_id, data.csv)
    if result["errors"]:
        raise HTTPException(
            422,
            "CSV预检失败："
            + "; ".join(
                f"第{x['row']}行：{x['message']}" for x in result["errors"][:5]
            ),
        )
    existing = {x.dedupe_key: x.data for x in records(db, workspace_id, "metric")}
    imported = 0
    duplicates = 0
    for row in result["rows"]:
        key = dedupe(row)
        if key in existing:
            if existing[key] != row:
                raise HTTPException(
                    409,
                    "预检后数据发生变化：相同 external_id 对应不同数据，本次导入未提交，请重新预检",
                )
            duplicates += 1
            continue
        create(db, workspace_id, "metric", row, dedupe=key)
        existing[key] = row
        imported += 1
    batch = create(
        db,
        workspace_id,
        "import",
        {
            "imported": imported,
            "duplicates": duplicates,
            "source": "csv",
            "rows": len(result["rows"]),
        },
    )
    audit(
        db,
        workspace_id,
        user,
        "csv-import",
        batch,
        {"imported": imported, "duplicates": duplicates},
    )
    return {"imported": imported, "duplicates": duplicates}


@router.get("/analytics")
def analytics_get(
    workspace_id: str, campaign_id: str | None = None, db=Depends(db_session)
):
    return analytics(db, workspace_id, campaign_id)


@router.post("/files", status_code=201, dependencies=[Depends(editor)])
async def upload(
    workspace_id: str,
    file: UploadFile = File(...),
    user=Depends(current_user),
    db=Depends(db_session),
):
    from pathlib import Path

    filename = Path((file.filename or "file").replace("\\", "/")).name
    extension = Path(filename).suffix.lower()
    allowed = {
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    if extension not in allowed:
        raise HTTPException(
            422, "仅支持纯文本、CSV、PNG、JPEG、WebP资料；不支持可执行文件、HTML或SVG"
        )
    content = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "文件不得超过10MiB")
    if not content:
        raise HTTPException(422, "文件不能为空")
    signatures = {
        ".png": b"\x89PNG\r\n\x1a\n",
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
    }
    if extension in signatures and not content.startswith(signatures[extension]):
        raise HTTPException(422, "文件内容与扩展名不匹配")
    if extension == ".webp" and not (
        content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    ):
        raise HTTPException(422, "WebP文件格式不正确")
    lowered = content.lower()
    if extension in (".txt", ".csv"):
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(422, "文本资料请使用UTF-8编码")
        if b"\x00" in content or any(
            token in lowered
            for token in (b"<script", b"<html", b"<svg", b"<!doctype", b"<iframe")
        ):
            raise HTTPException(422, "文本资料不得包含活动HTML/SVG内容")
    entity = create(
        db,
        workspace_id,
        "file",
        {"name": filename[:200], "size": len(content), "mime_type": allowed[extension]},
        blob=content,
    )
    audit(db, workspace_id, user, "upload", entity)
    return {"id": entity.id, **entity.data}


@router.get("/files/{id}")
def download(workspace_id: str, id: str, db=Depends(db_session)):
    from urllib.parse import quote

    entity = get_record(db, workspace_id, "file", id)
    return Response(
        entity.blob,
        media_type=entity.data["mime_type"],
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(entity.data["name"]),
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
