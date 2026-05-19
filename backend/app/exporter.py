from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from .config import settings
from .storage import Store


def safe_filename(value: str) -> str:
    keep = [char for char in value.strip() if char.isalnum() or char in "-_一二三四五六七八九十章回忆录"]
    return "".join(keep)[:60] or "chapter"


def _write_empty_mp3(target: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=16000",
            "-t",
            "0.2",
            "-codec:a",
            "libmp3lame",
            str(target),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _concat_wavs_to_mp3(wav_paths: list[Path], target: Path) -> None:
    if not wav_paths:
        _write_empty_mp3(target)
        return

    concat_file = target.with_suffix(".concat.txt")
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in wav_paths),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "3",
                str(target),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        concat_file.unlink(missing_ok=True)


def export_chapter(chapter_id: str, store: Store | None = None) -> Path:
    active_store = store or Store()
    chapter = active_store.get_chapter(chapter_id)
    if not chapter:
        raise KeyError(chapter_id)

    segments = active_store.list_segments(chapter_id)
    export_root = settings.export_dir / f"{safe_filename(chapter['title'])}-{chapter_id[:8]}"
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True, exist_ok=True)

    wav_paths = [settings.root_dir / segment["audio_path"] for segment in segments if segment["audio_path"]]
    mp3_path = export_root / "chapter.mp3"
    _concat_wavs_to_mp3([path for path in wav_paths if path.exists()], mp3_path)

    raw_text = "\n\n".join(segment["raw_text"] for segment in segments if segment["raw_text"].strip())
    cleaned_text = "\n\n".join(segment["cleaned_text"] for segment in segments if segment["cleaned_text"].strip())
    (export_root / "raw_asr.txt").write_text(raw_text, encoding="utf-8")
    (export_root / "cleaned_text.md").write_text(cleaned_text, encoding="utf-8")
    (export_root / "segments.json").write_text(
        json.dumps({"chapter": chapter, "segments": segments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    zip_path = settings.export_dir / f"{export_root.name}.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in export_root.iterdir():
            archive.write(path, arcname=path.name)

    active_store.update_chapter(chapter_id, status="completed")
    return zip_path
