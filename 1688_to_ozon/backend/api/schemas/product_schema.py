from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "crawldesk-backend"


class TranslateRequest(BaseModel):
    products: list[dict[str, Any]] = Field(default_factory=list)


class TranslateResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


class MapToOzonRequest(BaseModel):
    products: list[dict[str, Any]] = Field(default_factory=list)


class MapToOzonResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


class ExportRequest(BaseModel):
    products: list[dict[str, Any]] = Field(default_factory=list)
    file_name: str | None = None


class ExportResponse(BaseModel):
    file_id: str
    file_name: str
    download_url: str

