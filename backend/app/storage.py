from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .config import settings


def utc_now_sql() -> str:
    return "datetime('now')"


class Store:
    def __init__(self, db_path: Path = settings.db_path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chapters (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS segments (
                    id TEXT PRIMARY KEY,
                    chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    raw_text TEXT NOT NULL DEFAULT '',
                    cleaned_text TEXT NOT NULL DEFAULT '',
                    audio_path TEXT NOT NULL DEFAULT '',
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )

    def ensure_default_chapter(self) -> dict[str, Any]:
        chapters = self.list_chapters()
        if chapters:
            return chapters[0]
        return self.create_chapter("第一章")

    def list_chapters(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*,
                       COUNT(s.id) AS segment_count,
                       COALESCE(SUM(s.duration_ms), 0) AS duration_ms
                FROM chapters c
                LEFT JOIN segments s ON s.chapter_id = c.id
                GROUP BY c.id
                ORDER BY c.created_at ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_chapter(self, chapter_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM chapters WHERE id = ?",
                (chapter_id,),
            ).fetchone()
            return dict(row) if row else None

    def create_chapter(self, title: str, chapter_id: str | None = None) -> dict[str, Any]:
        import uuid

        new_id = chapter_id or str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO chapters (id, title) VALUES (?, ?)",
                (new_id, title),
            )
        return self.get_chapter(new_id) or {"id": new_id, "title": title, "status": "draft"}

    def update_chapter(self, chapter_id: str, title: str | None = None, status: str | None = None) -> dict[str, Any]:
        updates: list[str] = []
        values: list[Any] = []
        if title is not None:
            updates.append("title = ?")
            values.append(title)
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if updates:
            updates.append(f"updated_at = {utc_now_sql()}")
            values.append(chapter_id)
            with self.connect() as conn:
                conn.execute(f"UPDATE chapters SET {', '.join(updates)} WHERE id = ?", values)
        chapter = self.get_chapter(chapter_id)
        if not chapter:
            raise KeyError(chapter_id)
        return chapter

    def list_segments(self, chapter_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM segments
                WHERE chapter_id = ?
                ORDER BY position ASC, created_at ASC
                """,
                (chapter_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_segment(self, segment_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM segments WHERE id = ?", (segment_id,)).fetchone()
            return dict(row) if row else None

    def create_segment(
        self,
        chapter_id: str,
        raw_text: str,
        cleaned_text: str,
        audio_path: str,
        duration_ms: int,
        segment_id: str | None = None,
    ) -> dict[str, Any]:
        import uuid

        new_id = segment_id or str(uuid.uuid4())
        with self.connect() as conn:
            position = conn.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM segments WHERE chapter_id = ?",
                (chapter_id,),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO segments
                    (id, chapter_id, position, raw_text, cleaned_text, audio_path, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id, chapter_id, position, raw_text, cleaned_text, audio_path, duration_ms),
            )
        return self.get_segment(new_id) or {}

    def update_segment(self, segment_id: str, raw_text: str | None = None, cleaned_text: str | None = None) -> dict[str, Any]:
        updates: list[str] = []
        values: list[Any] = []
        if raw_text is not None:
            updates.append("raw_text = ?")
            values.append(raw_text)
        if cleaned_text is not None:
            updates.append("cleaned_text = ?")
            values.append(cleaned_text)
        if updates:
            updates.append(f"updated_at = {utc_now_sql()}")
            values.append(segment_id)
            with self.connect() as conn:
                conn.execute(f"UPDATE segments SET {', '.join(updates)} WHERE id = ?", values)
        segment = self.get_segment(segment_id)
        if not segment:
            raise KeyError(segment_id)
        return segment
