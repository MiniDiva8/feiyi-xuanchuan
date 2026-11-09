import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from .security import db_session, current_user, member, editor, owner
from .schemas import (
    KnowledgeInput,
    OfferingInput,
    CampaignInput,
    MemberInput,
    NextRound,
)
from .models import User, Membership, Workspace
from .workflow import records, get_record, public, create, audit
from .metrics import analytics

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}", dependencies=[Depends(member)]
)


@router.get("/settings")
def settings(workspace_id: str):
    return {
        "ai_configured": bool(os.getenv("MARKETING_AI_API_KEY")),
        "ai_model": os.getenv("MARKETING_AI_MODEL", ""),
        "publishing": "manual",
        "checkout": "external",
    }


@router.get("/overview")
def overview(workspace_id: str, db=Depends(db_session)):
    a = analytics(db, workspace_id)
    stats = a["stats"]
    return {
        "stats": {
            "campaigns": len(records(db, workspace_id, "campaign")),
            "pending_review": sum(
                x.data.get("status") == "draft"
                for kind in ("plan", "asset")
                for x in records(db, workspace_id, kind)
            ),
            "publications": len(records(db, workspace_id, "publication")),
            **{
                key: stats[key]
                for key in (
                    "revenue",
                    "spend",
                    "orders",
                    "registrations",
                    "impressions",
                    "interactions",
                )
            },
        },
        "trends": [
            {
                "date": x["date"],
                "impressions": x["impressions"],
                "revenue": x["revenue"],
            }
            for x in a["trends"]
        ],
        "recent_campaigns": [
            public(x) for x in records(db, workspace_id, "campaign")[-5:][::-1]
        ],
        "activity": [public(x) for x in records(db, workspace_id, "audit")[-10:][::-1]],
        "connections": {
            "ai_configured": bool(os.getenv("MARKETING_AI_API_KEY")),
            "publishing": "manual",
            "checkout": "external",
        },
    }


@router.get("/knowledge")
def knowledge_list(workspace_id: str, db=Depends(db_session)):
    return [public(x) for x in records(db, workspace_id, "knowledge")]


@router.post("/knowledge", status_code=201, dependencies=[Depends(editor)])
def knowledge_create(
    workspace_id: str,
    data: KnowledgeInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    if data.file_id:
        get_record(db, workspace_id, "file", data.file_id)
    entity = create(db, workspace_id, "knowledge", data.model_dump())
    audit(db, workspace_id, user, "create", entity)
    return public(entity)


@router.patch("/knowledge/{id}", dependencies=[Depends(editor)])
def knowledge_patch(
    workspace_id: str,
    id: str,
    data: dict,
    user=Depends(current_user),
    db=Depends(db_session),
):
    entity = get_record(db, workspace_id, "knowledge", id)
    updated = KnowledgeInput.model_validate({**entity.data, **data})
    if updated.file_id:
        get_record(db, workspace_id, "file", updated.file_id)
    before = entity.data
    entity.data = updated.model_dump()
    audit(
        db,
        workspace_id,
        user,
        "update",
        entity,
        {"before": before, "after": entity.data},
    )
    return public(entity)


@router.delete("/knowledge/{id}", dependencies=[Depends(editor)])
def knowledge_delete(
    workspace_id: str, id: str, user=Depends(current_user), db=Depends(db_session)
):
    entity = get_record(db, workspace_id, "knowledge", id)
    audit(db, workspace_id, user, "delete", entity, {"before": entity.data})
    db.delete(entity)
    return {"ok": True}


@router.get("/offerings")
def offering_list(workspace_id: str, db=Depends(db_session)):
    return [public(x) for x in records(db, workspace_id, "offering")]


@router.post("/offerings", status_code=201, dependencies=[Depends(editor)])
def offering_create(
    workspace_id: str,
    data: OfferingInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    entity = create(db, workspace_id, "offering", data.model_dump())
    audit(db, workspace_id, user, "create", entity)
    return public(entity)


@router.patch("/offerings/{id}", dependencies=[Depends(editor)])
def offering_patch(
    workspace_id: str,
    id: str,
    data: dict,
    user=Depends(current_user),
    db=Depends(db_session),
):
    entity = get_record(db, workspace_id, "offering", id)
    before = entity.data
    entity.data = OfferingInput.model_validate({**entity.data, **data}).model_dump()
    audit(
        db,
        workspace_id,
        user,
        "update",
        entity,
        {"before": before, "after": entity.data},
    )
    return public(entity)


@router.get("/campaigns")
def campaign_list(workspace_id: str, db=Depends(db_session)):
    return [public(x) for x in records(db, workspace_id, "campaign")]


@router.post("/campaigns", status_code=201, dependencies=[Depends(editor)])
def campaign_create(
    workspace_id: str,
    data: CampaignInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    if data.offering_id:
        get_record(db, workspace_id, "offering", data.offering_id)
    entity = create(
        db,
        workspace_id,
        "campaign",
        {**data.model_dump(mode="json"), "status": "draft"},
    )
    audit(db, workspace_id, user, "create", entity)
    return public(entity)


@router.get("/campaigns/{id}")
def campaign_get(workspace_id: str, id: str, db=Depends(db_session)):
    return public(get_record(db, workspace_id, "campaign", id))


@router.post(
    "/campaigns/{id}/next-round", status_code=201, dependencies=[Depends(editor)]
)
def next_round(
    workspace_id: str,
    id: str,
    data: NextRound,
    user=Depends(current_user),
    db=Depends(db_session),
):
    previous = get_record(db, workspace_id, "campaign", id)
    payload = {
        **previous.data,
        "name": data.name or previous.data["name"] + " · 下一轮",
        "previous_campaign_id": previous.id,
        "status": "draft",
    }
    entity = create(db, workspace_id, "campaign", payload)
    audit(db, workspace_id, user, "next-round", entity)
    return public(entity)


@router.get("/audit")
def audit_list(workspace_id: str, db=Depends(db_session)):
    return [public(x) for x in records(db, workspace_id, "audit")[::-1]]


@router.get("/members")
def members(workspace_id: str, db=Depends(db_session)):
    result = []
    for membership in db.scalars(
        select(Membership).where(Membership.workspace_id == workspace_id)
    ):
        user = db.get(User, membership.user_id)
        result.append(
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "role": membership.role,
            }
        )
    return result


@router.post("/members", status_code=201, dependencies=[Depends(owner)])
def member_create(
    workspace_id: str,
    data: MemberInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    target = db.scalar(select(User).where(User.email == data.email.lower()))
    if not target:
        raise HTTPException(422, "该账号尚未注册；此操作不发送邀请邮件")
    membership = db.get(Membership, (workspace_id, target.id))
    if membership:
        raise HTTPException(409, "该账号已是成员")
    db.add(Membership(workspace_id=workspace_id, user_id=target.id, role=data.role))
    entity = create(
        db, workspace_id, "membership-event", {"user_id": target.id, "role": data.role}
    )
    audit(db, workspace_id, user, "add-member", entity)
    return {
        "user_id": target.id,
        "name": target.name,
        "email": target.email,
        "role": data.role,
    }


@router.patch("/campaigns/{id}", dependencies=[Depends(editor)])
def campaign_patch(
    workspace_id: str,
    id: str,
    data: dict,
    user=Depends(current_user),
    db=Depends(db_session),
):
    entity = get_record(db, workspace_id, "campaign", id)
    original = {
        key: value
        for key, value in entity.data.items()
        if key in CampaignInput.model_fields
    }
    updated = CampaignInput.model_validate({**original, **data})
    if updated.offering_id:
        get_record(db, workspace_id, "offering", updated.offering_id)
    before = entity.data
    entity.data = {**entity.data, **updated.model_dump(mode="json")}
    audit(
        db,
        workspace_id,
        user,
        "update",
        entity,
        {"fields": sorted(data), "before": before, "after": entity.data},
    )
    return public(entity)
