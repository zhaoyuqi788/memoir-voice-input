from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import settings


@dataclass
class RecognizerResult:
    text: str
    is_endpoint: bool = False


class BaseRecognizer:
    ready: bool = False
    status: str = "not_loaded"

    def accept_pcm16(self, pcm_bytes: bytes) -> RecognizerResult:
        return RecognizerResult(text="", is_endpoint=False)

    def reset(self) -> None:
        return None


class DisabledRecognizer(BaseRecognizer):
    def __init__(self, reason: str):
        self.ready = False
        self.status = reason


def _find_model_dir() -> Path | None:
    configured = settings.sherpa_model_dir.strip()
    candidates: list[Path] = []
    if configured:
        configured_path = Path(configured)
        candidates.append(configured_path if configured_path.is_absolute() else settings.root_dir / configured_path)
    if settings.model_root.exists():
        candidates.extend(path for path in settings.model_root.iterdir() if path.is_dir())

    for candidate in candidates:
        if (candidate / "tokens.txt").exists() and list(candidate.glob("*.onnx")):
            return candidate
    return None


class SherpaOnlineRecognizer(BaseRecognizer):
    def __init__(self, model_dir: Path):
        import sherpa_onnx

        self.model_dir = model_dir
        model_file = next(model_dir.glob("*int8*.onnx"), None) or next(model_dir.glob("*.onnx"))
        tokens = model_dir / "tokens.txt"
        bpe_vocab = model_dir / "bbpe.model"

        model_config_kwargs = {
            "transducer": sherpa_onnx.OnlineTransducerModelConfig(encoder="", decoder="", joiner=""),
            "paraformer": sherpa_onnx.OnlineParaformerModelConfig(encoder="", decoder=""),
            "zipformer2_ctc": sherpa_onnx.OnlineZipformer2CtcModelConfig(model=str(model_file)),
            "tokens": str(tokens),
            "num_threads": settings.sherpa_num_threads,
            "debug": False,
            "model_type": "",
        }
        if bpe_vocab.exists():
            model_config_kwargs["bpe_vocab"] = str(bpe_vocab)

        try:
            model_config = sherpa_onnx.OnlineModelConfig(
                **model_config_kwargs,
                provider=settings.sherpa_provider,
            )
        except TypeError:
            model_config = sherpa_onnx.OnlineModelConfig(
                **model_config_kwargs,
                provider_config=sherpa_onnx.ProviderConfig(provider=settings.sherpa_provider),
            )

        recognizer_config = sherpa_onnx.OnlineRecognizerConfig(
            feat_config=sherpa_onnx.FeatureExtractorConfig(sampling_rate=16000, feature_dim=80),
            model_config=model_config,
            endpoint_config=sherpa_onnx.EndpointConfig(
                rule1=sherpa_onnx.EndpointRule(
                    must_contain_nonsilence=False,
                    min_trailing_silence=2.4,
                    min_utterance_length=0,
                ),
                rule2=sherpa_onnx.EndpointRule(
                    must_contain_nonsilence=True,
                    min_trailing_silence=1.2,
                    min_utterance_length=0,
                ),
                rule3=sherpa_onnx.EndpointRule(
                    must_contain_nonsilence=False,
                    min_trailing_silence=0,
                    min_utterance_length=20,
                ),
            ),
            enable_endpoint=True,
            decoding_method="greedy_search",
        )
        self.recognizer = sherpa_onnx.OnlineRecognizer(recognizer_config)
        self.stream = self.recognizer.create_stream()
        self.ready = True
        self.status = f"loaded:{model_dir.name}"

    def accept_pcm16(self, pcm_bytes: bytes) -> RecognizerResult:
        import numpy as np

        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        self.stream.accept_waveform(16000, samples)
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        result = self.recognizer.get_result(self.stream)
        text = getattr(result, "text", str(result)).strip()
        is_endpoint = bool(self.recognizer.is_endpoint(self.stream))
        if is_endpoint:
            self.recognizer.reset(self.stream)
        return RecognizerResult(text=text, is_endpoint=is_endpoint)

    def reset(self) -> None:
        self.recognizer.reset(self.stream)


def create_recognizer() -> BaseRecognizer:
    model_dir = _find_model_dir()
    if not model_dir:
        return DisabledRecognizer("模型未加载：请先下载中文 sherpa-onnx 模型并设置 SHERPA_MODEL_DIR。")
    try:
        return SherpaOnlineRecognizer(model_dir)
    except Exception as exc:  # pragma: no cover - depends on local native runtime/model files
        return DisabledRecognizer(f"模型加载失败：{exc}")
