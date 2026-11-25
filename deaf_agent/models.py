"""第六版本架構使用的資料物件。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InputEnvelope:
    """輸入與感測元件送入 Agent Runtime 的資料。"""

    timestamp: str
    audio_label: Optional[str] = None
    audio_text: Optional[str] = None
    direction: Optional[str] = None
    image_label: Optional[str] = None
    imu_state: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    source: str = "microphone_array"

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "InputEnvelope":
        return cls(
            timestamp=str(payload.get("timestamp", "unknown")),
            audio_label=payload.get("audio_label"),
            audio_text=payload.get("audio_text"),
            direction=payload.get("direction"),
            image_label=payload.get("image_label"),
            imu_state=payload.get("imu_state"),
            user_preferences=dict(payload.get("user_preferences") or {}),
            source=str(payload.get("source", "microphone_array")),
        )


@dataclass
class PreprocessedSignal:
    """音訊緩衝、降噪與 VAD 後的中間資料。"""

    timestamp: str
    audio_label: Optional[str]
    audio_text: Optional[str]
    image_label: Optional[str]
    direction: Optional[str]
    voice_activity: bool
    features: List[str]


@dataclass
class SoundPrediction:
    """專用聲音模型的統一輸出格式。"""

    label: str
    confidence: float
    model: str


@dataclass
class StructuredEvent:
    """Agent Runtime 對外輸出的結構化事件。"""

    event_type: str
    direction: str
    priority: str
    confidence: float
    timestamp: str
    source: str
    model_trace: List[str]
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OutputAction:
    """輸出與裝置驅動元件可執行的動作。"""

    channel: str
    action: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

