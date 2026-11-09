"""Application factory: uvicorn app.main:app --app-dir services/api --port 8010."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import configure
from .models import Record
from .security import RateLimiter, hash_password
from .routes_auth import router as auth_router
from .routes_workspace import router as workspace_router
from .routes_workflow import router as workflow_router
from .routes_data import router as data_router
from .routes_channels import router as channels_router
from .routes_video import router as video_router
from .video import MAX_VIDEO_BYTES

ROOT = Path(__file__).resolve().parents[3]


def create_app(database_url=None, storage_path=None):
    default = ROOT / ".data"
    default.mkdir(parents=True, exist_ok=True)
    url = (
        database_url
        or os.getenv("DATABASE_URL")
        or "sqlite:///" + str(default / "platform.db")
    )
    engine, sessions = configure(url)

    @asynccontextmanager
    async def lifespan(app):
        with sessions() as db:
            for task in db.scalars(select(Record).where(Record.kind == "task")):
                if task.data.get("status") in ("running", "queued"):
                    task.data = {
                        **task.data,
                        "status": "failed",
                        "error": "服务重启中断了此任务，可在尝试次数限制内重试",
                    }
            db.commit()
        yield
        engine.dispose()

    app = FastAPI(title="非遗商家营销平台", version="1.0.0", lifespan=lifespan)
    app.state.sessions = sessions
    app.state.engine = engine
    app.state.limiter = RateLimiter()
    app.state.secure_cookie = os.getenv("SESSION_SECURE", "false").lower() == "true"
    app.state.dummy_password = hash_password("dummy-password-never-used")
    trusted = {
        x.strip().rstrip("/")
        for x in os.getenv("TRUSTED_ORIGINS", "").split(",")
        if x.strip()
    }

    @app.middleware("http")
    async def protections(request: Request, call_next):
        if request.url.path.startswith("/api") and request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            origin = request.headers.get("origin")
            expected = str(request.base_url).rstrip("/")
            if request.headers.get("sec-fetch-site") == "cross-site" or (
                origin and origin.rstrip("/") not in (trusted | {expected})
            ):
                return JSONResponse(
                    {"detail": "请求来源不受信任，请从本工作台操作"}, status_code=403
                )
            try:
                limit = 11 * 1024 * 1024
                if (request.method == "POST" and request.url.path.startswith("/api/workspaces/")
                        and request.url.path.endswith("/video-analyses")):
                    limit = MAX_VIDEO_BYTES
                if int(request.headers.get("content-length", "0")) > limit:
                    return JSONResponse({"detail": "请求体过大"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "请求体大小无效"}, status_code=400)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            {
                "detail": "输入格式不正确："
                + "; ".join(
                    ".".join(str(v) for v in error["loc"]) + " " + error["msg"]
                    for error in exc.errors()[:5]
                )
            },
            status_code=422,
        )

    @app.exception_handler(ValidationError)
    async def model_error(request, exc):
        return JSONResponse(
            {
                "detail": "字段格式不正确："
                + "; ".join(error["msg"] for error in exc.errors()[:5])
            },
            status_code=422,
        )

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({"detail": "记录冲突或重复，请刷新后重试"}, status_code=409)

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        return JSONResponse(
            {"detail": "服务暂时无法完成请求，请稍后重试"}, status_code=500
        )

    @app.get("/api/health")
    def health():
        return {"ok": True}

    for router in (auth_router, workspace_router, workflow_router, data_router, channels_router, video_router):
        app.include_router(router)
    dist = ROOT / "apps/web/dist"

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "接口不存在")
        target = (dist / path).resolve()
        if target.is_relative_to(dist.resolve()) and target.is_file():
            return FileResponse(target)
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        raise HTTPException(404, "前端尚未构建，请先运行前端生产构建")

    return app


app = create_app()
