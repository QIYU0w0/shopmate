from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=6, max_length=64)


class UserOut(BaseModel):
    id: int
    username: str
    created_at: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class SessionSummary(BaseModel):
    id: str
    title: str
    category: str
    created_at: str
    updated_at: str
    last_message_preview: str = ""


class ChatSendRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1000)


class ChatMessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str


class SourceRecordOut(BaseModel):
    source_name: str
    provider: str
    source_url: str
    notes: str


class ProductOut(BaseModel):
    id: str
    title: str
    brand: str
    platform: str
    price: float
    image_url: str
    product_url: str
    source_count: int
    matched_keywords: list[str]
    score: float
    category: str
    highlights: list[str]
    dynamic_facets: dict[str, list[str]]
    source_records: list[SourceRecordOut]


class FacetOption(BaseModel):
    value: str
    count: int


class FacetDefinition(BaseModel):
    key: str
    label: str
    type: Literal["enum", "range", "tag"]
    options: list[FacetOption] = Field(default_factory=list)
    chart: Literal["bar", "pie", "list"] = "bar"


class SessionFacetResponse(BaseModel):
    category: str
    fixed: list[FacetDefinition]
    dynamic: list[FacetDefinition]


class ChartDatum(BaseModel):
    label: str
    value: float


class SessionStatsResponse(BaseModel):
    session_id: str
    total_products: int
    average_price: float
    chart_groups: dict[str, list[ChartDatum]]


class ProductDetailResponse(ProductOut):
    session_id: str
    task_id: str
