"""命令列入口：讀取 JSON 並印出完整資料流結果。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from .pipeline import AgentRuntime


DEMO_PAYLOAD: Dict[str, Any] = {
    "timestamp": "2026-11-25T12:00:00+08:00",
    "audio_label": "horn",
    "direction": "left",
    "imu_state": "walking",
    "user_preferences": {"priority_overrides": {"horn": "attention"}},
    "source": "microphone_array",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Deaf Agent data-flow prototype")
    parser.add_argument("--demo", action="store_true", help="使用內建的道路喇叭示範資料")
    args = parser.parse_args()

    if args.demo:
        payload = DEMO_PAYLOAD
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            parser.error("請從 stdin 傳入 JSON，或使用 --demo")
        payload = json.loads(raw)

    result = AgentRuntime().run(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

