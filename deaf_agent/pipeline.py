"""依照第六版本架構圖串起輸入、模型、Agent 與輸出的資料流。"""

from __future__ import annotations

import base64
import csv
import io
import struct
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .models import (
    InputEnvelope,
    OutputAction,
    PreprocessedSignal,
    SoundPrediction,
    StructuredEvent,
)


class AudioPreprocessor:
    """音訊緩衝區、降噪 / VAD 與格式統一。"""

    def process(self, data: InputEnvelope) -> PreprocessedSignal:
        label = (data.audio_label or "unknown").strip().lower()
        level = data.audio_level if isinstance(data.audio_level, (int, float)) else 0.0
        has_signal = label not in {"", "unknown", "silence", "none"} or level > 0.02
        features = ["audio_frame", "denoised_signal"]
        if data.audio_text:
            features.append("speech_text_candidate")
        if data.image_label:
            features.append("image_frame")
        return PreprocessedSignal(
            timestamp=data.timestamp,
            audio_label=data.audio_label,
            audio_text=data.audio_text,
            image_label=data.image_label,
            direction=data.direction,
            audio_level=float(level),
            audio_samples=_decode_wav_base64(data.audio_wav_base64),
            sample_rate=16000,
            voice_activity=has_signal,
            features=features,
        )


def _decode_wav_base64(encoded: str | None) -> List[float] | None:
    """解碼網頁送來的單聲道 16-bit WAV；沒有音檔時回傳 None。"""
    if not encoded:
        return None
    try:
        raw = base64.b64decode(encoded, validate=True)
        with wave_open(io.BytesIO(raw)) as wav:
            frames = wav.readframes(wav.getnframes())
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                return None
            values = struct.unpack(f"<{len(frames) // 2}h", frames)
            samples = [sample / 32768.0 for sample in values]
            source_rate = wav.getframerate()
            if source_rate == 16000 or not samples:
                return samples
            output_length = max(1, round(len(samples) * 16000 / source_rate))
            step = (len(samples) - 1) / max(1, output_length - 1)
            resampled = []
            for index in range(output_length):
                position = index * step
                left = int(position)
                right = min(left + 1, len(samples) - 1)
                fraction = position - left
                resampled.append(samples[left] * (1 - fraction) + samples[right] * fraction)
            return resampled
    except (ValueError, EOFError, OSError, struct.error):
        return None


def wave_open(stream: io.BytesIO):
    # Imported here so the rest of the demo path stays dependency-free.
    import wave

    return wave.open(stream, "rb")


class SoundClassifier:
    """YAMNet / PANNs / AST 的可替換介面。

    目前先用明確的規則式 fallback，讓資料流可以在沒有模型權重時執行。
    接入真實模型時，只需要替換 ``predict``，輸出格式不變。
    """

    MODEL_NAME = "YAMNet / PANNs / AST"

    def __init__(self) -> None:
        self._yamnet = None
        self._yamnet_labels: List[str] = []
        self._yamnet_error: str | None = None

    def status(self) -> Dict[str, Any]:
        return {
            "demo": "ready",
            "yamnet": "ready" if self._yamnet is not None else ("error" if self._yamnet_error else "not_loaded"),
            "yamnet_error": self._yamnet_error,
        }

    def _load_yamnet(self) -> None:
        if self._yamnet is not None or self._yamnet_error:
            return
        try:
            import tensorflow_hub as hub

            self._yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
            self._yamnet_labels = self._load_labels()
        except Exception as exc:  # optional dependency/model download
            self._yamnet_error = str(exc)

    @staticmethod
    def _load_labels() -> List[str]:
        url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
        try:
            text = urllib.request.urlopen(url, timeout=10).read().decode("utf-8")
            rows = list(csv.DictReader(io.StringIO(text)))
            return [row.get("display_name", "unknown") for row in rows]
        except Exception:
            return []

    def _predict_yamnet(self, signal: PreprocessedSignal) -> SoundPrediction:
        self._load_yamnet()
        if self._yamnet is None:
            return SoundPrediction(
                label="ambient_sound",
                confidence=0.0,
                model="YAMNet",
                status=f"unavailable: {self._yamnet_error}",
            )
        if not signal.audio_samples:
            return SoundPrediction(label="ambient_sound", confidence=0.0, model="YAMNet", status="no_audio")
        try:
            import numpy as np

            waveform = np.asarray(signal.audio_samples, dtype=np.float32)
            scores, _, _ = self._yamnet(waveform)
            mean_scores = np.mean(scores.numpy(), axis=0)
            index = int(np.argmax(mean_scores))
            raw_label = self._yamnet_labels[index] if index < len(self._yamnet_labels) else f"class_{index}"
            label = self._normalize_label(raw_label)
            return SoundPrediction(label=label, confidence=float(mean_scores[index]), model=f"YAMNet: {raw_label}", status="ready")
        except Exception as exc:
            return SoundPrediction(label="ambient_sound", confidence=0.0, model="YAMNet", status=f"error: {exc}")

    @staticmethod
    def _normalize_label(label: str) -> str:
        raw = label.lower()
        if "horn" in raw or "honking" in raw:
            return "horn"
        if "siren" in raw:
            return "siren"
        if "alarm" in raw:
            return "alarm"
        if "announcement" in raw:
            return "announcement"
        if "speech" in raw or "conversation" in raw:
            return "speech"
        return "ambient_sound"

    def predict(self, signal: PreprocessedSignal, backend: str = "demo") -> SoundPrediction:
        if backend.lower() == "yamnet":
            return self._predict_yamnet(signal)
        raw = (signal.audio_label or "unknown").lower()
        label = "ambient_sound"
        confidence = 0.55
        for candidate in ("horn", "siren", "alarm", "speech", "announcement", "doorbell", "loud_event"):
            if candidate in raw:
                label = "loud_sound" if candidate == "loud_event" else candidate
                confidence = 0.70 if candidate == "loud_event" else 0.90
                break
        return SoundPrediction(label=label, confidence=confidence, model=self.MODEL_NAME, status="demo")


class DirectionEstimator:
    """DOA / 麥克風陣列方向估計介面。"""

    MODEL_NAME = "DOA / microphone array"

    def estimate(self, signal: PreprocessedSignal) -> Tuple[str, str]:
        direction = (signal.direction or "unknown").lower()
        if direction not in {"left", "right", "front", "back", "unknown"}:
            direction = "unknown"
        return direction, self.MODEL_NAME


class ContextBuilder:
    """把模型結果、感測狀態與使用者偏好組成上下文。"""

    def build(
        self,
        data: InputEnvelope,
        signal: PreprocessedSignal,
        prediction: SoundPrediction,
        direction: str,
    ) -> Dict[str, Any]:
        return {
            "event_type": prediction.label,
            "direction": direction,
            "confidence": prediction.confidence,
            "imu_state": data.imu_state,
            "audio_level": signal.audio_level,
            "image_label": signal.image_label,
            "features": signal.features,
            "user_preferences": data.user_preferences,
            "model_backend": data.model_backend,
            "model_status": prediction.status,
        }


@dataclass
class PolicyState:
    """Policy / State Store 的最小記憶版本。"""

    default_priority: str = "attention"

    def priority_for(self, event_type: str, preferences: Dict[str, Any]) -> str:
        preferred = preferences.get("priority_overrides", {})
        if isinstance(preferred, dict) and event_type in preferred:
            return str(preferred[event_type])
        if event_type in {"siren", "alarm"}:
            return "urgent"
        if event_type in {"horn", "announcement", "loud_sound"}:
            return "attention"
        return self.default_priority


class PlannerRouter:
    """依優先級選擇回饋介面。"""

    def plan(self, event: StructuredEvent) -> List[OutputAction]:
        direction = event.direction
        actions = [
            OutputAction(
                channel="ui_display",
                action="show_event",
                payload={
                    "text": f"{event.event_type}｜方向：{direction}",
                    "priority": event.priority,
                    "confidence": event.confidence,
                },
            ),
            OutputAction(
                channel="haptic_driver",
                action="vibrate",
                payload={"pattern": event.priority, "direction": direction},
            ),
            OutputAction(
                channel="led_light_driver",
                action="set_status",
                payload={"status": event.priority},
            ),
        ]
        return actions


class AgentRuntime:
    """第六版本架構的最小 Agent Orchestrator。"""

    def __init__(self) -> None:
        self.preprocessor = AudioPreprocessor()
        self.classifier = SoundClassifier()
        self.direction_estimator = DirectionEstimator()
        self.context_builder = ContextBuilder()
        self.policy_state = PolicyState()
        self.planner_router = PlannerRouter()

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = InputEnvelope.from_dict(payload)
        signal = self.preprocessor.process(data)
        prediction = self.classifier.predict(signal, backend=data.model_backend)
        direction, direction_model = self.direction_estimator.estimate(signal)
        context = self.context_builder.build(data, signal, prediction, direction)
        priority = self.policy_state.priority_for(prediction.label, data.user_preferences)
        event = StructuredEvent(
            event_type=prediction.label,
            direction=direction,
            priority=priority,
            confidence=prediction.confidence,
            timestamp=data.timestamp,
            source=data.source,
            model_trace=[prediction.model, direction_model],
            context=context,
        )
        actions = self.planner_router.plan(event)
        return {
            "input": payload,
            "preprocessing": {
                "voice_activity": signal.voice_activity,
                "features": signal.features,
                "sample_rate": signal.sample_rate,
            },
            "structured_event": event.to_dict(),
            "model_status": prediction.status,
            "model_registry": self.classifier.status(),
            "output_actions": [action.to_dict() for action in actions],
        }

