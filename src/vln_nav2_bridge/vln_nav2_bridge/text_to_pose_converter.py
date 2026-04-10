import json
import re
from typing import Dict, Optional, Tuple


class TextToPoseConverter:
    """Convert model output text into safe map-frame target coordinates."""

    def __init__(self, min_xy: float = -3.0, max_xy: float = 4.0) -> None:
        self.min_xy = min_xy
        self.max_xy = max_xy
        self._fallback_targets: Dict[str, Tuple[float, float, float]] = {
            "purple box": (2.8, 3.0, 0.0),
            "purple boxes": (2.8, 3.0, 0.0),
            "shelf": (2.5, 2.5, 0.0),
            "right shelf": (3.0, 2.2, 0.0),
            "chair": (0.2, 0.0, 1.57),
            "office chair": (0.2, 0.0, 1.57),
            "plant": (-0.7, 0.1, 1.57),
            "robot": (0.0, 0.0, 0.0),
            "center": (0.0, 0.0, 0.0),
        }

    def convert(self, instruction: str, model_output: str) -> Dict[str, object]:
        """Return dict with x, y, yaw and conversion metadata."""
        parsed = self._parse_json_pose(model_output)
        method = "json"

        if parsed is None:
            parsed = self._fallback_from_text(instruction, model_output)
            method = "fallback"

        if parsed is None:
            return {
                "ok": False,
                "reason": "No pose found in model output and fallback rules did not match.",
            }

        x, y, yaw = parsed
        if not self._is_safe(x, y):
            return {
                "ok": False,
                "reason": (
                    f"Target out of safe range: x={x:.2f}, y={y:.2f}, "
                    f"allowed=[{self.min_xy}, {self.max_xy}]"
                ),
                "method": method,
            }

        return {
            "ok": True,
            "x": x,
            "y": y,
            "yaw": yaw,
            "method": method,
        }

    def _parse_json_pose(self, text: str) -> Optional[Tuple[float, float, float]]:
        candidates = re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL)
        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            if "x" not in data or "y" not in data:
                continue

            try:
                x = float(data["x"])
                y = float(data["y"])
                yaw = float(data.get("yaw", 0.0))
            except (TypeError, ValueError):
                continue

            return (x, y, yaw)

        return None

    def _fallback_from_text(self, instruction: str, model_output: str) -> Optional[Tuple[float, float, float]]:
        combined = f"{instruction}\n{model_output}".lower()
        for key, pose in self._fallback_targets.items():
            if key in combined:
                return pose
        return None

    def _is_safe(self, x: float, y: float) -> bool:
        return self.min_xy <= x <= self.max_xy and self.min_xy <= y <= self.max_xy
