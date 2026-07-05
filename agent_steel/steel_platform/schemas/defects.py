from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DefectSample(BaseModel):
    """产线单条缺陷检测结果（Agent 校验所需核心字段）。"""

    defect_class: str = Field(..., description="缺陷类别")
    batch_id: str = Field(..., description="批次号")
    timestamp: datetime = Field(..., description="检测时间")
    position_mm: float = Field(..., description="沿轧向位置 mm")
    line_id: str = Field(..., description="产线")
    camera_id: str = Field(..., description="相机位")
    embedding: list[float] | None = Field(
        default=None, description="缺陷 ROI embedding，可为空由上游后补"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DefectIngestPayload(BaseModel):
    """缺陷检测模块 → Agent：单批或增量推送。"""

    samples: list[DefectSample]


class ValidationResult(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    normalized_samples: list[DefectSample] = Field(default_factory=list)


class SessionMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    ts: datetime | None = None


class ChatRequest(BaseModel):
    session_id: str
    question: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    intent: str | None = None
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
