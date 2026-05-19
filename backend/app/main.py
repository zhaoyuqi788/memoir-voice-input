from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .audio import write_wav
from .config import settings
from .exporter import export_chapter
from .recognizer import create_recognizer
from .schemas import ChapterCreate, ChapterOut, ChapterUpdate, ExportOut, SegmentUpdate
from .segmentation import SilenceSegmenter, pcm_duration_ms
from .storage import Store
from .text_cleanup import clean_transcript

app = FastAPI(title="memoir-voice-input", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = Store()
recognizer = create_recognizer()


@app.on_event("startup")
def startup() -> None:
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    store.ensure_default_chapter()


def chapter_with_segments(chapter: dict) -> dict:
    enriched = dict(chapter)
    enriched["segments"] = store.list_segments(chapter["id"])
    enriched.setdefault("segment_count", len(enriched["segments"]))
    enriched.setdefault("duration_ms", sum(segment["duration_ms"] for segment in enriched["segments"]))
    return enriched


@app.get("/api/health")
def health() -> dict[str, str | bool]:
    return {"ok": True, "recognizer_ready": recognizer.ready, "recognizer_status": recognizer.status}


@app.get("/api/chapters", response_model=list[ChapterOut])
def list_chapters() -> list[dict]:
    chapters = store.list_chapters()
    if not chapters:
        chapters = [store.ensure_default_chapter()]
    return [chapter_with_segments(chapter) for chapter in chapters]


@app.post("/api/chapters", response_model=ChapterOut)
def create_chapter(payload: ChapterCreate) -> dict:
    return chapter_with_segments(store.create_chapter(payload.title))


@app.patch("/api/chapters/{chapter_id}", response_model=ChapterOut)
def update_chapter(chapter_id: str, payload: ChapterUpdate) -> dict:
    try:
        return chapter_with_segments(store.update_chapter(chapter_id, title=payload.title, status=payload.status))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@app.patch("/api/segments/{segment_id}")
def update_segment(segment_id: str, payload: SegmentUpdate) -> dict:
    try:
        return store.update_segment(segment_id, raw_text=payload.raw_text, cleaned_text=payload.cleaned_text)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Segment not found") from exc


@app.get("/api/segments/{segment_id}/audio")
def segment_audio(segment_id: str) -> FileResponse:
    segment = store.get_segment(segment_id)
    if not segment or not segment["audio_path"]:
        raise HTTPException(status_code=404, detail="Segment audio not found")
    path = settings.root_dir / segment["audio_path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Segment audio file missing")
    return FileResponse(path, media_type="audio/wav", filename=f"{segment_id}.wav")


@app.post("/api/chapters/{chapter_id}/complete", response_model=ExportOut)
def complete_chapter(chapter_id: str) -> dict:
    try:
        zip_path = export_chapter(chapter_id, store=store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    return {
        "chapter_id": chapter_id,
        "export_path": str(zip_path.relative_to(settings.root_dir)),
        "download_url": f"/api/chapters/{chapter_id}/export.zip",
    }


@app.get("/api/chapters/{chapter_id}/export.zip")
def download_export(chapter_id: str) -> FileResponse:
    chapter = store.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    matching = sorted(settings.export_dir.glob(f"*-{chapter_id[:8]}.zip"))
    if not matching:
        zip_path = export_chapter(chapter_id, store=store)
    else:
        zip_path = matching[-1]
    return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)


async def _send_status(websocket: WebSocket, message: str) -> None:
    await websocket.send_json({"type": "status", "message": message, "recognizerReady": recognizer.ready})


@app.websocket("/ws/asr")
async def asr_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    current_chapter_id: str | None = None
    current_pcm = bytearray()
    current_text = ""
    segmenter = SilenceSegmenter(
        silence_ms=settings.segment_silence_ms,
        min_audio_ms=settings.segment_min_audio_ms,
        energy_threshold=settings.segment_energy_threshold,
    )

    async def finalize_segment(reason: str) -> None:
        nonlocal current_pcm, current_text, segmenter
        raw_text = current_text.strip()
        if not current_chapter_id or not current_pcm or not raw_text:
            current_pcm = bytearray()
            current_text = ""
            segmenter.reset()
            return

        cleaned = clean_transcript(raw_text)
        duration_ms = pcm_duration_ms(bytes(current_pcm))
        segment_id_hint = f"{current_chapter_id}-{len(store.list_segments(current_chapter_id)) + 1:04d}"
        relative_audio = Path("data") / "audio" / current_chapter_id / f"{segment_id_hint}.wav"
        absolute_audio = settings.root_dir / relative_audio
        write_wav(absolute_audio, bytes(current_pcm))
        segment = store.create_segment(
            chapter_id=current_chapter_id,
            raw_text=raw_text,
            cleaned_text=cleaned,
            audio_path=str(relative_audio),
            duration_ms=duration_ms,
        )
        await websocket.send_json({"type": "segment", "reason": reason, "segment": segment})
        current_pcm = bytearray()
        current_text = ""
        segmenter.reset()

    try:
        await _send_status(websocket, recognizer.status)
        while True:
            message = await websocket.receive()
            if message.get("text") is not None:
                payload = json.loads(message["text"])
                message_type = payload.get("type")
                if message_type == "start":
                    current_chapter_id = payload.get("chapterId")
                    recognizer.reset()
                    await _send_status(websocket, "正在收音")
                elif message_type == "stop":
                    await finalize_segment("stop")
                    await _send_status(websocket, "已暂停")
                elif message_type == "commit":
                    await finalize_segment("manual")
                elif message_type == "reset":
                    current_pcm = bytearray()
                    current_text = ""
                    segmenter.reset()
                    recognizer.reset()
                    await _send_status(websocket, "已重置")
                continue

            chunk = message.get("bytes")
            if not chunk:
                continue
            current_pcm.extend(chunk)
            result = recognizer.accept_pcm16(chunk)
            if result.text:
                current_text = result.text
                await websocket.send_json({"type": "partial", "text": current_text})
            should_finalize = result.is_endpoint or segmenter.ingest(chunk, current_text)
            if should_finalize:
                await finalize_segment("pause")
    except WebSocketDisconnect:
        return
