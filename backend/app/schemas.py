from __future__ import annotations

from pydantic import BaseModel, Field


class SegmentOut(BaseModel):
    id: str
    chapter_id: str
    position: int
    raw_text: str
    cleaned_text: str
    audio_path: str
    duration_ms: int
    created_at: str
    updated_at: str


class ChapterOut(BaseModel):
    id: str
    title: str
    status: str = "draft"
    created_at: str
    updated_at: str
    segment_count: int = 0
    duration_ms: int = 0
    segments: list[SegmentOut] = Field(default_factory=list)


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ChapterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = None


class SegmentUpdate(BaseModel):
    raw_text: str | None = None
    cleaned_text: str | None = None


class ExportOut(BaseModel):
    chapter_id: str
    export_path: str
    download_url: str
