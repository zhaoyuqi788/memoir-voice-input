from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT_DIR
    data_dir: Path = ROOT_DIR / "data"
    audio_dir: Path = ROOT_DIR / "data" / "audio"
    export_dir: Path = ROOT_DIR / "exports"
    model_root: Path = ROOT_DIR / "models"
    db_path: Path = ROOT_DIR / "data" / "memoir.sqlite3"
    sherpa_model_dir: str = ""
    sherpa_provider: str = "cpu"
    sherpa_num_threads: int = 2
    segment_silence_ms: int = 1200
    segment_min_audio_ms: int = 700
    segment_energy_threshold: int = 550

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            sherpa_model_dir=os.getenv("SHERPA_MODEL_DIR", ""),
            sherpa_provider=os.getenv("SHERPA_PROVIDER", "cpu"),
            sherpa_num_threads=int(os.getenv("SHERPA_NUM_THREADS", "2")),
            segment_silence_ms=int(os.getenv("SEGMENT_SILENCE_MS", "1200")),
            segment_min_audio_ms=int(os.getenv("SEGMENT_MIN_AUDIO_MS", "700")),
            segment_energy_threshold=int(os.getenv("SEGMENT_ENERGY_THRESHOLD", "550")),
        )


settings = Settings.from_env()
