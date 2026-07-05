from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from steel_platform.schemas.defects import DefectSample
from steel_platform.schemas.events import AnomalyEvent


def _ts_epoch(ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp()


class EventRuleEngine:
    """
    异常事件识别层（简化规则）：
    - 同类缺陷在滑动窗口内连续出现 >= N 次
    - 或短时间窗口内同类计数突增 >= burst
    """

    def __init__(
        self,
        consecutive_n: int = 3,
        burst_window_sec: float = 60.0,
        burst_min_count: int = 5,
    ) -> None:
        self.consecutive_n = consecutive_n
        self.burst_window_sec = burst_window_sec
        self.burst_min_count = burst_min_count

    def evaluate(self, samples: list[DefectSample]) -> AnomalyEvent | None:
        if not samples:
            return None

        ordered = sorted(samples, key=lambda s: s.timestamp)
        n = self.consecutive_n
        if len(ordered) >= n:
            for i in range(len(ordered) - n + 1):
                window = ordered[i : i + n]
                if len({s.defect_class for s in window}) == 1:
                    return self._build_event(
                        window,
                        reason=f"同类缺陷「{window[0].defect_class}」在时序上连续出现 {n} 次",
                        rule_metadata={"rule": "consecutive_same_class", "run_len": n},
                    )

        #  burst：最近 burst_window_sec 内同类数量
        last_epoch = _ts_epoch(ordered[-1].timestamp)

        for cls in {s.defect_class for s in ordered}:
            recent = [
                s
                for s in ordered
                if s.defect_class == cls
                and (last_epoch - _ts_epoch(s.timestamp)) <= self.burst_window_sec
            ]
            if len(recent) >= self.burst_min_count:
                return self._build_event(
                    recent,
                    reason=f"{self.burst_window_sec:.0f}s 内同类「{cls}」计数 {len(recent)}（阈值 {self.burst_min_count}）",
                    rule_metadata={"rule": "burst_count", "class": cls, "count": len(recent)},
                )

        return None

    def _build_event(
        self,
        window_samples: list[DefectSample],
        reason: str,
        rule_metadata: dict[str, Any],
    ) -> AnomalyEvent:
        ref = window_samples[-1]
        return AnomalyEvent(
            event_id=str(uuid.uuid4()),
            reason=reason,
            triggered_at=datetime.now(timezone.utc),
            line_id=ref.line_id,
            camera_id=ref.camera_id,
            defect_class=ref.defect_class,
            window_samples=window_samples,
            rule_metadata=rule_metadata,
        )
