from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CrawlOptions(BaseModel):
    input_mode: Literal["keyword", "product_url", "shop_url"] | None = None
    max_links: int = Field(default=5, ge=1, le=50)
    translate_to_russian: bool = True
    map_to_ozon: bool = True
    export_excel: bool = False
    generate_hashtags: bool = True
    template_name: str | None = None


class CrawlRequest(BaseModel):
    platform: str = Field(..., examples=["1688", "shein", "etsy", "ebay"])
    keyword: str | None = None
    product_url: str | None = None
    shop_url: str | None = None
    options: CrawlOptions = Field(default_factory=CrawlOptions)


class CrawlAcceptedResponse(BaseModel):
    job_id: str
    status: str
    message: str


class CrawlStatusResponse(BaseModel):
    job_id: str
    status: str
    message: str | None = None
    error: str | None = None
    progress: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class CrawlResultResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None

