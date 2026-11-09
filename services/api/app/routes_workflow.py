import copy, html
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from .security import db_session, current_user, member, editor, reviewer
from .schemas import (
    Instructions,
    RevisePlan,
    AssetInput,
    ReviseAsset,
    Reject,
    PublicationInput,
)
from .workflow import (
    records,
    get_record,
    public,
    create,
    audit,
    next_version,
    latest,
    snapshot,
    context,
    valid_plan,
    valid_asset,
    run_generation,
    validate_plan_content,
    knowledge,
)

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}", dependencies=[Depends(member)]
)


def generation_limit(request, w):
    request.app.state.limiter.check(("generate", w), limit=30, window=3600)


@router.get("/campaigns/{id}/plans")
def plans(workspace_id: str, id: str, db=Depends(db_session)):
    get_record(db, workspace_id, "campaign", id)
    return [public(x) for x in records(db, workspace_id, "plan", id)]


@router.post(
    "/campaigns/{id}/plans/generate", status_code=201, dependencies=[Depends(editor)]
)
def generate_plan(
    workspace_id: str,
    id: str,
    data: Instructions,
    request: Request,
    user=Depends(current_user),
    db=Depends(db_session),
):
    generation_limit(request, workspace_id)
    return public(
        run_generation(
            db,
            workspace_id,
            user,
            "plan",
            get_record(db, workspace_id, "campaign", id),
            data.model_dump(),
        )
    )


@router.post("/plans/{id}/revise", status_code=201, dependencies=[Depends(editor)])
def revise_plan(
    workspace_id: str,
    id: str,
    data: RevisePlan,
    request: Request,
    user=Depends(current_user),
    db=Depends(db_session),
):
    old = get_record(db, workspace_id, "plan", id)
    campaign = get_record(db, workspace_id, "campaign", old.data["campaign_id"])
    if data.content is None:
        generation_limit(request, workspace_id)
        return public(
            run_generation(db, workspace_id, user, "plan", campaign, data.model_dump())
        )
    validated = validate_plan_content(db, workspace_id, campaign, data.content)
    entity = create(
        db,
        workspace_id,
        "plan",
        {
            "campaign_id": campaign.id,
            "content": validated,
            "status": "draft",
            "generation_mode": old.data["generation_mode"],
            "_snapshot": snapshot(db, workspace_id, campaign),
            "_source_snapshot": {
                key: value
                for key, value in context(db, workspace_id, campaign).items()
                if key in ("knowledge", "offering", "campaign")
            },
        },
        campaign.id,
        next_version(db, workspace_id, "plan", campaign.id),
    )
    audit(db, workspace_id, user, "revise", entity, {"previous_version_id": old.id})
    return public(entity)


@router.post("/plans/{id}/approve", dependencies=[Depends(reviewer)])
def approve_plan(
    workspace_id: str, id: str, user=Depends(current_user), db=Depends(db_session)
):
    plan = get_record(db, workspace_id, "plan", id)
    valid_plan(db, plan, approved=False)
    if plan.data["status"] != "draft":
        raise HTTPException(409, "该方案已审核；修改须创建新版本")
    plan.data = {**plan.data, "status": "approved"}
    audit(db, workspace_id, user, "approve", plan)
    return public(plan)


@router.post("/plans/{id}/reject", dependencies=[Depends(reviewer)])
def reject_plan(
    workspace_id: str,
    id: str,
    data: Reject,
    user=Depends(current_user),
    db=Depends(db_session),
):
    plan = get_record(db, workspace_id, "plan", id)
    if not latest(db, plan) or plan.data["status"] != "draft":
        raise HTTPException(409, "仅最新待审核方案可以驳回")
    plan.data = {**plan.data, "status": "rejected"}
    audit(db, workspace_id, user, "reject", plan, {"reason": data.reason})
    return public(plan)


@router.get("/campaigns/{id}/assets")
def assets(workspace_id: str, id: str, db=Depends(db_session)):
    get_record(db, workspace_id, "campaign", id)
    return [
        public(x)
        for x in records(db, workspace_id, "asset")
        if x.data["campaign_id"] == id
    ]


@router.post(
    "/campaigns/{id}/assets/generate", status_code=201, dependencies=[Depends(editor)]
)
def generate_asset(
    workspace_id: str,
    id: str,
    data: AssetInput,
    request: Request,
    user=Depends(current_user),
    db=Depends(db_session),
):
    generation_limit(request, workspace_id)
    return public(
        run_generation(
            db,
            workspace_id,
            user,
            "asset",
            get_record(db, workspace_id, "campaign", id),
            data.model_dump(),
        )
    )


@router.post("/assets/{id}/revise", status_code=201, dependencies=[Depends(editor)])
def revise_asset(
    workspace_id: str,
    id: str,
    data: ReviseAsset,
    user=Depends(current_user),
    db=Depends(db_session),
):
    old = get_record(db, workspace_id, "asset", id)
    plan = get_record(db, workspace_id, "plan", old.data["plan_id"])
    campaign = valid_plan(db, plan)
    from marketing_ai.engine import check_content

    body = data.body
    title = data.title if data.title is not None else old.data["title"]
    checks = check_content(
        title + "\n" + body, context(db, workspace_id, campaign, plan=public(plan))
    )
    content = copy.deepcopy(old.data["content"])
    content["body"] = body
    content["title"] = title
    # Existing generated poster markup is not carried over after the reviewed text changes.
    content.pop("svg", None)
    content.pop("html", None)
    payload = {
        **old.data,
        "title": title,
        "body": body,
        "content": content,
        "checks": checks,
        "status": "draft",
    }
    entity = create(
        db,
        workspace_id,
        "asset",
        payload,
        old.parent_id,
        next_version(db, workspace_id, "asset", old.parent_id),
    )
    audit(db, workspace_id, user, "revise", entity, {"previous_version_id": old.id})
    return public(entity)


@router.post("/assets/{id}/approve", dependencies=[Depends(reviewer)])
def approve_asset(
    workspace_id: str, id: str, user=Depends(current_user), db=Depends(db_session)
):
    asset = get_record(db, workspace_id, "asset", id)
    valid_asset(db, asset, approved=False)
    if asset.data["status"] != "draft":
        raise HTTPException(409, "该素材已审核；修改须创建新版本")
    asset.data = {**asset.data, "status": "approved"}
    audit(db, workspace_id, user, "approve", asset)
    return public(asset)


@router.post("/assets/{id}/reject", dependencies=[Depends(reviewer)])
def reject_asset(
    workspace_id: str,
    id: str,
    data: Reject,
    user=Depends(current_user),
    db=Depends(db_session),
):
    asset = get_record(db, workspace_id, "asset", id)
    if not latest(db, asset) or asset.data["status"] != "draft":
        raise HTTPException(409, "仅最新待审核素材可以驳回")
    asset.data = {**asset.data, "status": "rejected"}
    audit(db, workspace_id, user, "reject", asset, {"reason": data.reason})
    return public(asset)


@router.get("/assets/{id}/export")
def export(
    workspace_id: str,
    id: str,
    format: str = "txt",
    user=Depends(current_user),
    db=Depends(db_session),
):
    asset = get_record(db, workspace_id, "asset", id)
    valid_asset(db, asset)
    title = asset.data["title"]
    body = asset.data["body"]
    if format == "txt":
        output = title + "\n\n" + body
        mime = "text/plain"
    elif format == "html":
        output = (
            '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'
            + html.escape(title)
            + "</title><main><h1>"
            + html.escape(title)
            + '</h1><p style="white-space:pre-wrap">'
            + html.escape(body)
            + "</p></main></html>"
        )
        mime = "text/html"
    elif format == "svg":
        from .poster import render_poster
        from .models import Workspace

        workspace = db.get(Workspace, workspace_id)
        output = render_poster(title, body, asset.data["channel"], workspace.name)
        mime = "image/svg+xml"
    else:
        raise HTTPException(422, "不支持的导出格式")
    audit(db, workspace_id, user, "export", asset, {"format": format})
    return Response(
        output,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="asset-{asset.id}.{format}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        },
    )


@router.get("/publications")
def publications(workspace_id: str, db=Depends(db_session)):
    return [public(x) for x in records(db, workspace_id, "publication")]


@router.post("/publications", status_code=201, dependencies=[Depends(editor)])
def publication_create(
    workspace_id: str,
    data: PublicationInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    asset = get_record(db, workspace_id, "asset", data.asset_id)
    valid_asset(db, asset)
    if data.channel != asset.data["channel"]:
        raise HTTPException(422, "发布渠道须与审核素材渠道一致")
    entity = create(
        db,
        workspace_id,
        "publication",
        {
            **data.model_dump(mode="json"),
            "campaign_id": asset.data["campaign_id"],
            "plan_id": asset.data["plan_id"],
        },
    )
    audit(db, workspace_id, user, "manual-publication", entity)
    return public(entity)


@router.get("/campaigns/{id}/reviews")
def reviews(workspace_id: str, id: str, db=Depends(db_session)):
    get_record(db, workspace_id, "campaign", id)
    return [public(x) for x in records(db, workspace_id, "review", id)]


@router.post(
    "/campaigns/{id}/reviews/generate", status_code=201, dependencies=[Depends(editor)]
)
def review_generate(
    workspace_id: str,
    id: str,
    request: Request,
    user=Depends(current_user),
    db=Depends(db_session),
):
    generation_limit(request, workspace_id)
    return public(
        run_generation(
            db,
            workspace_id,
            user,
            "review",
            get_record(db, workspace_id, "campaign", id),
            {},
        )
    )


@router.get("/tasks")
def tasks(workspace_id: str, db=Depends(db_session)):
    return [public(x) for x in records(db, workspace_id, "task")[::-1]]


@router.post("/tasks/{id}/retry", dependencies=[Depends(editor)])
def retry(
    workspace_id: str,
    id: str,
    request: Request,
    user=Depends(current_user),
    db=Depends(db_session),
):
    task = get_record(db, workspace_id, "task", id)
    if task.data["status"] != "failed":
        raise HTTPException(409, "仅失败任务可以重试")
    if task.data.get("_attempts", 0) >= 3:
        raise HTTPException(409, "已达到最多3次尝试，请检查配置后新建任务")
    generation_limit(request, workspace_id)
    run_generation(
        db,
        workspace_id,
        user,
        task.data["kind"],
        get_record(db, workspace_id, "campaign", task.data["_campaign_id"]),
        task.data["_payload"],
        task,
    )
    return public(task)
