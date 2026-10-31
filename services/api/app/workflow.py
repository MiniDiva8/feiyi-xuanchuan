"""Shared tenant-scoped record access and immutable marketing workflow."""

import hashlib, json, sys
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select, func, update
from .models import Record, Workspace

AI_PATH = Path(__file__).resolve().parents[2] / "marketing-ai"
if str(AI_PATH) not in sys.path:
    sys.path.insert(0, str(AI_PATH))


def records(db, w, kind, parent=None):
    query = select(Record).where(Record.workspace_id == w, Record.kind == kind)
    if parent is not None:
        query = query.where(Record.parent_id == parent)
    return list(db.scalars(query.order_by(Record.created_at, Record.id)))


def get_record(db, w, kind, id):
    record = db.scalar(
        select(Record).where(
            Record.id == id, Record.workspace_id == w, Record.kind == kind
        )
    )
    if not record:
        raise HTTPException(404, "记录不存在或无权访问")
    return record


def public(record):
    return {
        **{k: v for k, v in record.data.items() if not k.startswith("_")},
        "id": record.id,
        "workspace_id": record.workspace_id,
        "created_at": record.created_at,
        **({"version": record.version} if record.version else {}),
    }


def create(db, w, kind, data, parent=None, version=None, dedupe=None, blob=None):
    record = Record(
        workspace_id=w,
        kind=kind,
        data=data,
        parent_id=parent,
        version=version,
        dedupe_key=dedupe,
        blob=blob,
    )
    db.add(record)
    db.flush()
    return record


def audit(db, w, user, action, entity, details=None):
    create(
        db,
        w,
        "audit",
        {
            "action": action,
            "entity_type": entity.kind,
            "entity_id": entity.id,
            "actor_name": user.name,
            "details": details or {},
        },
    )


def next_version(db, w, kind, parent):
    return (
        db.scalar(
            select(func.max(Record.version)).where(
                Record.workspace_id == w,
                Record.kind == kind,
                Record.parent_id == parent,
            )
        )
        or 0
    ) + 1


def latest(db, record):
    return (
        record.version
        == next_version(db, record.workspace_id, record.kind, record.parent_id) - 1
    )


def knowledge(db, w):
    return [
        public(x)
        for x in records(db, w, "knowledge")
        if x.data["confirmed"] and x.data["usage_scope"] == "marketing"
    ]


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def snapshot(db, w, campaign):
    offering = (
        get_record(db, w, "offering", campaign.data["offering_id"])
        if campaign.data.get("offering_id")
        else None
    )
    return digest(
        {
            "knowledge": knowledge(db, w),
            "offering": public(offering) if offering else None,
            "campaign": public(campaign),
        }
    )


def context(db, w, campaign, **extra):
    workspace = db.get(Workspace, w)
    offering = (
        get_record(db, w, "offering", campaign.data["offering_id"])
        if campaign.data.get("offering_id")
        else None
    )
    return {
        "workspace": {"id": w, "name": workspace.name},
        "campaign": public(campaign),
        "offering": public(offering) if offering else None,
        "knowledge": knowledge(db, w),
        "plan": None,
        **extra,
    }


def ensure_offering(db, w, campaign):
    objective = campaign.data["objective"]
    offering_id = campaign.data.get("offering_id")
    if objective in ("sales", "registration") and not offering_id:
        raise HTTPException(
            409, "销售或报名活动须先关联真实商品或课程及承接入口，请新建完整活动"
        )
    if not offering_id:
        return
    offering = get_record(db, w, "offering", offering_id)
    expected = {"sales": "product", "registration": "course"}.get(objective)
    if expected and offering.data["kind"] != expected:
        raise HTTPException(409, "销售须关联商品，报名须关联课程")
    if offering.data["quantity"] <= 0:
        raise HTTPException(409, "关联商品库存或课程名额须大于0，请更新后重新生成审核")
    from .schemas import http_url

    try:
        http_url(offering.data["conversion_url"])
    except ValueError:
        raise HTTPException(409, "关联商品或课程缺少有效承接入口")


def validate_plan_content(db, w, campaign, content):
    from datetime import date
    from decimal import Decimal
    from .schemas import PlanContent

    data = PlanContent.model_validate(content).model_dump(mode="json")
    allowed = set(campaign.data["channels"])
    for row in data["channels"] + data["schedule"]:
        if row["channel"] not in allowed:
            raise HTTPException(422, "方案含活动未允许的渠道")
    plan_channels = {row["channel"] for row in data["channels"]}
    for row in data["schedule"]:
        if row["channel"] not in plan_channels:
            raise HTTPException(422, "日程渠道未列入方案")
        if not campaign.data["start_date"] <= row["day"] <= campaign.data["end_date"]:
            raise HTTPException(422, "方案日程超出活动期间")
    if sum(Decimal(str(row["amount"])) for row in data["budget"]) > Decimal(
        str(campaign.data["budget"])
    ):
        raise HTTPException(422, "方案预算超过活动预算")
    allowed_evidence = {item["id"]: item for item in knowledge(db, w)}
    for row in data["evidence"]:
        item = allowed_evidence.get(row["id"])
        if not item or item["title"] != row["title"] or item["source"] != row["source"]:
            raise HTTPException(
                422, "方案引用了未确认、不可营销使用或不属于当前商家的资料"
            )
    from marketing_ai.engine import check_content

    if any(
        check.get("level") == "error"
        for check in check_content(
            json.dumps(data, ensure_ascii=False), context(db, w, campaign)
        )
    ):
        raise HTTPException(422, "方案包含缺少来源或不允许的宣传表述")
    return data


def valid_plan(db, plan, approved=True):
    if not latest(db, plan) or (approved and plan.data["status"] != "approved"):
        raise HTTPException(409, "需要最新版本已批准方案，请重新审核")
    campaign = get_record(db, plan.workspace_id, "campaign", plan.data["campaign_id"])
    ensure_offering(db, plan.workspace_id, campaign)
    if plan.data.get("_snapshot") != snapshot(db, plan.workspace_id, campaign):
        raise HTTPException(409, "资料来源或产品课程已变化，请修订方案并重新审核")
    return campaign


def valid_asset(db, asset, approved=True):
    if not latest(db, asset) or (approved and asset.data["status"] != "approved"):
        raise HTTPException(409, "需要最新版本已批准素材，请重新审核")
    plan = get_record(db, asset.workspace_id, "plan", asset.data["plan_id"])
    valid_plan(db, plan)
    if any(x.get("level") == "error" for x in asset.data.get("checks", [])):
        raise HTTPException(409, "素材检查存在错误，须修订后重新审核")
    return plan


def ai_call(kind, ctx):
    from marketing_ai import engine

    function = {
        "plan": engine.generate_plan,
        "asset": engine.generate_asset,
        "review": engine.build_review,
    }[kind]
    result = function(ctx)
    if not isinstance(result, dict) or result.get("generation_mode") not in (
        "template",
        "ai",
    ):
        raise RuntimeError("生成服务返回无效结果")
    return result


def run_generation(db, w, user, kind, campaign, payload, task=None):
    """Persist the job before network; never retain a DB transaction during AI I/O."""
    ctx = context(db, w, campaign, instructions=payload.get("instructions", ""))
    before = snapshot(db, w, campaign)
    plan = None
    if kind == "asset":
        plan = get_record(db, w, "plan", payload["plan_id"])
        if plan.data["campaign_id"] != campaign.id:
            raise HTTPException(422, "方案与活动不匹配")
        valid_plan(db, plan)
        allowed_channels = {
            row["channel"] for row in plan.data["content"]["channels"]
        } & set(campaign.data["channels"])
        if payload["channel"] not in allowed_channels:
            raise HTTPException(422, "素材渠道未列入活动及已批准方案")
        ctx.update(plan=public(plan), channel=payload["channel"], kind=payload["kind"])
    if kind == "review":
        from .metrics import analytics

        ctx["analytics"] = analytics(db, w, campaign.id)
    if task is None:
        task = create(
            db,
            w,
            "task",
            {
                "kind": kind,
                "status": "running",
                "_payload": payload,
                "_campaign_id": campaign.id,
                "_attempts": 1,
            },
        )
        db.commit()
    else:
        attempts = task.data.get("_attempts", 0)
        claimed = {
            **task.data,
            "status": "running",
            "error": None,
            "_attempts": attempts + 1,
        }
        outcome = db.execute(
            update(Record)
            .where(
                Record.id == task.id,
                Record.workspace_id == w,
                Record.kind == "task",
                Record.data["status"].as_string() == "failed",
                Record.data["_attempts"].as_integer() == attempts,
                Record.data["_attempts"].as_integer() < 3,
            )
            .values(data=claimed)
            .execution_options(synchronize_session=False)
        )
        if outcome.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "任务已被其他请求处理或达到重试上限")
        db.commit()
        db.refresh(task)
    try:
        result = ai_call(kind, ctx)
    except Exception:
        task.data = {
            **task.data,
            "status": "failed",
            "error": "生成服务失败，请检查模型配置或稍后重试；未替换为虚构结果",
        }
        db.commit()
        raise HTTPException(502, "生成服务失败，可在任务列表重试")
    db.expire_all()
    campaign = get_record(db, w, "campaign", campaign.id)
    if snapshot(db, w, campaign) != before:
        task.data = {
            **task.data,
            "status": "failed",
            "error": "生成期间资料发生变化，请重试",
        }
        db.commit()
        raise HTTPException(409, "生成期间资料发生变化，请重试")
    if kind == "asset":
        try:
            valid_plan(db, get_record(db, w, "plan", plan.id))
        except HTTPException:
            task.data = {
                **task.data,
                "status": "failed",
                "error": "生成期间方案审核状态发生变化",
            }
            db.commit()
            raise
    try:
        if kind == "plan":
            data = {
                "campaign_id": campaign.id,
                "status": "draft",
                "generation_mode": result["generation_mode"],
                "content": validate_plan_content(db, w, campaign, result["content"]),
                "_snapshot": before,
                "_source_snapshot": {
                    "knowledge": ctx["knowledge"],
                    "offering": ctx["offering"],
                    "campaign": ctx["campaign"],
                },
            }
            entity = create(
                db,
                w,
                "plan",
                data,
                campaign.id,
                next_version(db, w, "plan", campaign.id),
            )
        elif kind == "asset":
            data = {
                k: result[k]
                for k in ("title", "body", "content", "checks", "generation_mode")
            }
            data.update(
                campaign_id=campaign.id,
                plan_id=plan.id,
                status="draft",
                channel=payload["channel"],
                kind=payload["kind"],
            )
            group = digest(
                {
                    "campaign_id": campaign.id,
                    "channel": payload["channel"],
                    "kind": payload["kind"],
                }
            )
            entity = create(
                db, w, "asset", data, group, next_version(db, w, "asset", group)
            )
        else:
            entity = create(
                db,
                w,
                "review",
                {
                    "campaign_id": campaign.id,
                    "generation_mode": result["generation_mode"],
                    "content": result["content"],
                },
                campaign.id,
            )
        task.data = {
            **task.data,
            "status": "succeeded",
            "generation_mode": result["generation_mode"],
            "usage": result.get("usage", {}),
            "_result_id": entity.id,
        }
        audit(
            db,
            w,
            user,
            "generate",
            entity,
            {"generation_mode": result["generation_mode"]},
        )
        db.commit()
        return entity
    except (KeyError, TypeError, ValueError, HTTPException):
        db.rollback()
        task = get_record(db, w, "task", task.id)
        task.data = {**task.data, "status": "failed", "error": "生成结果不符合接口要求"}
        db.commit()
        raise HTTPException(502, "生成结果不符合接口要求")
