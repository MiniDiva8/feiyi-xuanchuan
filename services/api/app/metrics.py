import csv, io
from collections import defaultdict
from fastapi import HTTPException
from pydantic import ValidationError
from .schemas import MetricInput
from .workflow import records, get_record, digest

NUMBERS = [
    "impressions",
    "views",
    "reads",
    "interactions",
    "inquiries",
    "reservations",
    "leads",
    "orders",
    "revenue",
    "refunds",
    "registrations",
    "checkins",
    "spend",
]


def validate_metric(db, w, data):
    get_record(db, w, "campaign", data["campaign_id"])
    if data.get("publication_id"):
        publication = get_record(db, w, "publication", data["publication_id"])
        if publication.data["campaign_id"] != data["campaign_id"]:
            raise HTTPException(422, "发布记录与活动不匹配")


def dedupe(data):
    return (
        "external:" + data["external_id"]
        if data.get("external_id")
        else "row:" + digest(data)
    )


def preview(db, w, text):
    errors = []
    valid = []
    duplicates = 0
    existing = {x.dedupe_key: x.data for x in records(db, w, "metric")}
    seen = {}
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
        if not reader.fieldnames or len(reader.fieldnames) != len(
            set(reader.fieldnames)
        ):
            return {
                "rows": [],
                "errors": [{"row": 1, "message": "缺少表头或表头重复"}],
                "duplicates": 0,
                "valid_rows": 0,
            }
        allowed = set(MetricInput.model_fields)
        if set(reader.fieldnames) - allowed:
            return {
                "rows": [],
                "errors": [{"row": 1, "message": "含不支持的表头"}],
                "duplicates": 0,
                "valid_rows": 0,
            }
        for rownum, row in enumerate(reader, 2):
            if rownum > 10001:
                errors.append({"row": rownum, "message": "每次最多导入10000行"})
                break
            try:
                if None in row:
                    raise ValueError("列数与表头不符")
                cleaned = {
                    key: value.strip()
                    for key, value in row.items()
                    if value is not None and value.strip() != ""
                }
                data = MetricInput.model_validate(cleaned).model_dump(mode="json")
                validate_metric(db, w, data)
                key = dedupe(data)
                previous = seen.get(key) or existing.get(key)
                if previous is not None:
                    if previous != data:
                        errors.append(
                            {
                                "row": rownum,
                                "message": "相同 external_id 对应不同数据，请核对来源后使用正确唯一标识",
                            }
                        )
                        continue
                    duplicates += 1
                seen[key] = data
                valid.append(data)
            except (ValidationError, ValueError, HTTPException) as exc:
                message = (
                    exc.detail
                    if isinstance(exc, HTTPException)
                    else "字段格式或数值不正确，请检查日期、关联活动和非负数字"
                )
                errors.append({"row": rownum, "message": str(message)})
    except csv.Error:
        errors.append({"row": len(valid) + 2, "message": "CSV格式不正确"})
    return {
        "rows": valid,
        "errors": errors,
        "duplicates": duplicates,
        "valid_rows": len(valid),
    }


def analytics(db, w, campaign_id=None):
    if campaign_id:
        get_record(db, w, "campaign", campaign_id)
    rows = [
        x.data
        for x in records(db, w, "metric")
        if not campaign_id or x.data["campaign_id"] == campaign_id
    ]
    stats = {key: round(sum(row.get(key, 0) for row in rows), 2) for key in NUMBERS}
    stats["net_revenue"] = round(stats["revenue"] - stats["refunds"], 2)
    stats["unknown_revenue"] = round(
        sum(row["revenue"] for row in rows if row["attribution"] == "unknown"), 2
    )
    dates = defaultdict(lambda: {"impressions": 0, "revenue": 0, "spend": 0})
    channels = defaultdict(
        lambda: {
            "impressions": 0,
            "interactions": 0,
            "orders": 0,
            "revenue": 0,
            "spend": 0,
        }
    )
    for row in rows:
        for key in dates[row["date"]]:
            dates[row["date"]][key] += row[key]
        for key in channels[row["channel"]]:
            channels[row["channel"]][key] += row[key]
    return {
        "stats": stats,
        "trends": [
            {"date": day, **{key: round(value, 2) for key, value in data.items()}}
            for day, data in sorted(dates.items())
        ],
        "channels": [
            {
                "channel": channel,
                **{key: round(value, 2) for key, value in data.items()},
            }
            for channel, data in sorted(channels.items())
        ],
        "records": len(rows),
    }
