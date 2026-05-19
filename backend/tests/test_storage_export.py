from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.app.audio import write_wav
from backend.app.exporter import safe_filename
from backend.app.storage import Store


class StorageExportTest(unittest.TestCase):
    def test_create_chapter_and_segment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "memoir.sqlite3")
            chapter = store.create_chapter("童年")
            segment = store.create_segment(
                chapter_id=chapter["id"],
                raw_text="原始文字",
                cleaned_text="整理文字。",
                audio_path="data/audio/test.wav",
                duration_ms=1200,
            )
            self.assertEqual(segment["position"], 1)
            self.assertEqual(len(store.list_segments(chapter["id"])), 1)

    def test_safe_filename_keeps_chinese(self) -> None:
        self.assertEqual(safe_filename("第一章：小时候 / 雪"), "第一章小时候雪")

    def test_write_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.wav"
            write_wav(path, b"\0\0" * 1600)
            self.assertTrue(os.path.getsize(path) > 44)


if __name__ == "__main__":
    unittest.main()
