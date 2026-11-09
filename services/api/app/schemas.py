from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(Input):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=256)
    workspace_name: str = Field(min_length=1, max_length=120)


class Login(Input):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class WorkspaceInput(Input):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)


class KnowledgeInput(Input):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=100000)
    source: str = Field(min_length=1, max_length=2000)
    usage_scope: Literal["marketing", "internal"]
    confirmed: bool
    kind: Literal["fact", "brand", "material"]
    file_id: str | None = None


class OfferingInput(Input):
    kind: Literal["product", "course"]
    name: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=10000)
    price: float = Field(ge=0, allow_inf_nan=False)
    quantity: int = Field(ge=0, strict=True)
    location: str = Field(max_length=1000)
    delivery: str = Field(max_length=2000)
    conversion_url: str

    @field_validator("conversion_url")
    @classmethod
    def url(cls, v):
        return http_url(v)


class CampaignInput(Input):
    name: str = Field(min_length=1, max_length=300)
    objective: Literal["sales", "registration", "awareness"]
    audience: str = Field(min_length=1, max_length=3000)
    start_date: date
    end_date: date
    budget: float = Field(ge=0, allow_inf_nan=False)
    channels: list[str] = Field(min_length=1, max_length=20)
    offering_id: str | None = None
    notes: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def dates(self):
        if self.end_date < self.start_date:
            raise ValueError("结束日期不得早于开始日期")
        if any(not x.strip() or len(x) > 100 for x in self.channels):
            raise ValueError("渠道不能为空或过长")
        return self


class Instructions(Input):
    instructions: str = Field(default="", max_length=10000)


class RevisePlan(Instructions):
    content: dict | None = None


class AssetInput(Instructions):
    plan_id: str
    channel: str = Field(min_length=1, max_length=100)
    kind: Literal["copy", "poster", "script"]


class ReviseAsset(Input):
    title: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1, max_length=50000)


class Reject(Input):
    reason: str = Field(min_length=1, max_length=2000)


class PublicationInput(Input):
    asset_id: str
    channel: str = Field(min_length=1, max_length=100)
    url: str
    published_at: datetime
    external_id: str | None = None

    @field_validator("url")
    @classmethod
    def url_check(cls, v):
        return http_url(v)

    @field_validator("published_at")
    @classmethod
    def timezone_check(cls, v):
        if v.tzinfo is None:
            raise ValueError("发布时间需要时区")
        return v


class PlanChannel(Input):
    channel: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=16000)
    content_ideas: list[str] = Field(max_length=40)


class PlanSchedule(Input):
    day: date
    action: str = Field(min_length=1, max_length=16000)
    channel: str = Field(min_length=1, max_length=100)


class PlanBudget(Input):
    item: str = Field(min_length=1, max_length=16000)
    amount: float = Field(ge=0, allow_inf_nan=False)

    @field_validator("amount", mode="before")
    @classmethod
    def not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("预算必须为数字")
        return value


class Evidence(Input):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    source: str = Field(min_length=1, max_length=2000)


class PlanContent(Input):
    theme: str = Field(min_length=1, max_length=16000)
    summary: str = Field(min_length=1, max_length=16000)
    audience: str = Field(min_length=1, max_length=16000)
    channels: list[PlanChannel] = Field(min_length=1, max_length=60)
    schedule: list[PlanSchedule] = Field(min_length=1, max_length=60)
    budget: list[PlanBudget] = Field(min_length=1, max_length=60)
    warnings: list[str] = Field(max_length=60)
    evidence: list[Evidence] = Field(max_length=1000)


class MetricInput(Input):
    campaign_id: str
    publication_id: str | None = None
    date: date
    channel: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=2000)
    external_id: str | None = Field(default=None, max_length=300)
    attribution: Literal["known", "unknown"]
    impressions: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    reads: int = Field(default=0, ge=0)
    interactions: int = Field(default=0, ge=0)
    inquiries: int = Field(default=0, ge=0)
    reservations: int = Field(default=0, ge=0)
    leads: int = Field(default=0, ge=0)
    orders: int = Field(default=0, ge=0)
    revenue: float = Field(default=0, ge=0, allow_inf_nan=False)
    refunds: float = Field(default=0, ge=0, allow_inf_nan=False)
    registrations: int = Field(default=0, ge=0)
    checkins: int = Field(default=0, ge=0)
    spend: float = Field(default=0, ge=0, allow_inf_nan=False)

    @field_validator("publication_id", "external_id", mode="before")
    @classmethod
    def empty_optional(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator(
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
        mode="before",
    )
    @classmethod
    def numeric_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("指标必须是数字，不能是布尔值")
        return value

    @model_validator(mode="after")
    def related(self):
        if self.refunds > self.revenue:
            raise ValueError("退款不得超过收入")
        if self.checkins > self.registrations:
            raise ValueError("核销不得超过报名")
        return self


class CSVInput(Input):
    csv: str = Field(max_length=5 * 1024 * 1024)


class MemberInput(Input):
    email: str = Field(max_length=254)
    role: Literal["editor", "reviewer"]


class NextRound(Input):
    name: str | None = Field(default=None, max_length=300)


def http_url(value):
    from urllib.parse import urlsplit

    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("https", "http")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("请输入有效 http(s) 链接")
    return value
