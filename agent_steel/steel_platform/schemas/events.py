from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from steel_platform.schemas.defects import DefectSample


class AnomalyEvent(BaseModel):
    """事件规则引擎输出的异常事件。"""

    event_id: str
    reason: str
    triggered_at: datetime
    line_id: str
    camera_id: str
    defect_class: str
    window_samples: list[DefectSample]
    rule_metadata: dict[str, Any] = Field(default_factory=dict)


class EventWindowSummary(BaseModel):
    """Skill 用的事件窗口聚合摘要。"""

    defect_class: str
    line_id: str
    camera_id: str
    window_start: datetime
    window_end: datetime
    sample_count: int
    event_embedding: list[float]
    positions_mm: list[float]
