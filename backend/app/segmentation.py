from __future__ import annotations

from array import array
from dataclasses import dataclass
from math import sqrt

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2


def pcm_duration_ms(pcm_bytes: bytes) -> int:
    sample_count = len(pcm_bytes) // BYTES_PER_SAMPLE
    return int(sample_count / SAMPLE_RATE * 1000)


def pcm_rms(pcm_bytes: bytes) -> float:
    if not pcm_bytes:
        return 0.0
    samples = array("h")
    samples.frombytes(pcm_bytes)
    if len(samples) == 0:
        return 0.0
    return sqrt(sum(sample * sample for sample in samples) / len(samples))


@dataclass
class SilenceSegmenter:
    silence_ms: int = 1200
    min_audio_ms: int = 700
    energy_threshold: int = 550
    elapsed_ms: int = 0
    last_voice_ms: int = 0
    saw_voice: bool = False
    pending_text: str = ""

    def ingest(self, pcm_bytes: bytes, partial_text: str = "") -> bool:
        duration = pcm_duration_ms(pcm_bytes)
        self.elapsed_ms += duration
        if partial_text:
            self.pending_text = partial_text

        if pcm_rms(pcm_bytes) >= self.energy_threshold:
            self.saw_voice = True
            self.last_voice_ms = self.elapsed_ms

        trailing_silence = self.elapsed_ms - self.last_voice_ms
        enough_audio = self.elapsed_ms >= self.min_audio_ms
        has_text = bool(self.pending_text.strip())
        return self.saw_voice and enough_audio and has_text and trailing_silence >= self.silence_ms

    def reset(self) -> None:
        self.elapsed_ms = 0
        self.last_voice_ms = 0
        self.saw_voice = False
        self.pending_text = ""
