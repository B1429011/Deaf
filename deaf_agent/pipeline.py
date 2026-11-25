"""依照第六版本架構圖串起輸入、模型、Agent 與輸出的資料流。"""

from __future__ import annotations

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
            voice_activity=has_signal,
            features=features,
        )


class SoundClassifier:
    """YAMNet / PANNs / AST 的可替換介面。

    目前先用明確的規則式 fallback，讓資料流可以在沒有模型權重時執行。
    接入真實模型時，只需要替換 ``predict``，輸出格式不變。
    """

    MODEL_NAME = "YAMNet / PANNs / AST"

    def predict(self, signal: PreprocessedSignal) -> SoundPrediction:
        raw = (signal.audio_label or "unknown").lower()
        label = "ambient_sound"
        confidence = 0.55
        for candidate in ("horn", "siren", "alarm", "speech", "announcement", "doorbell"):
            if candidate in raw:
                label = candidate
                confidence = 0.90
                break
        return SoundPrediction(label=label, confidence=confidence, model=self.MODEL_NAME)


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
        if event_type in {"horn", "announcement"}:
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
        prediction = self.classifier.predict(signal)
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
            },
            "structured_event": event.to_dict(),
            "output_actions": [action.to_dict() for action in actions],
        }

