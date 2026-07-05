from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from steel_platform.agent.orchestrator import run_chat
from steel_platform.schemas.analysis import PeriodicDefectAnalysis
from steel_platform.schemas.defects import (
    ChatRequest,
    ChatResponse,
    DefectIngestPayload,
    SessionMessage,
    ValidationResult,
)
from steel_platform.schemas.events import AnomalyEvent
from steel_platform.services.event_engine import EventRuleEngine
from steel_platform.services.ingest_validator import validate_defect_payload
from steel_platform.skills.periodic_defect import run_periodic_defect_skill

app = FastAPI(title="Steel Defect Agent Platform", version="0.1.0")

SESSIONS: dict[str, list[SessionMessage]] = {}
ENGINE = EventRuleEngine(consecutive_n=3, burst_window_sec=120.0, burst_min_count=5)


class IngestResponse(BaseModel):
    validation: ValidationResult
    event: AnomalyEvent | None = None
    analysis: PeriodicDefectAnalysis | None = None
    logs: list[str] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/defects/ingest", response_model=IngestResponse)
def ingest_defects(payload: DefectIngestPayload) -> IngestResponse:
    """
    流程 A 前半：产线/检测模块 → 校验 → 事件规则；若触发事件则执行周期性缺陷 Skill。
    """
    logs: list[str] = []
    vr = validate_defect_payload(payload)
    if not vr.ok:
        logs.append("校验失败，已记录（此处返回 errors，可接运维通知）。")
        return IngestResponse(validation=vr, logs=logs)

    logs.append("校验通过，进入事件规则引擎。")
    event = ENGINE.evaluate(vr.normalized_samples)
    analysis: PeriodicDefectAnalysis | None = None
    if event:
        logs.append(f"事件触发：{event.event_id}，原因：{event.reason}")
        analysis = run_periodic_defect_skill(event)
        logs.append("周期性缺陷 Skill 已完成（Mock 工具链）。")
    else:
        logs.append("未满足异常事件规则，本次不触发 Agent Skill。")

    return IngestResponse(validation=vr, event=event, analysis=analysis, logs=logs)


@app.post("/v1/agent/chat", response_model=ChatResponse)
def agent_chat(req: ChatRequest) -> ChatResponse:
    """流程 B：前端 HTTP → session 记忆 → 意图路由 → 工具(Mock) → 自然语言。"""
    hist = SESSIONS.setdefault(req.session_id, [])
    hist.append(SessionMessage(role="user", content=req.question, ts=None))
    resp = run_chat(req.session_id, req.question)
    hist.append(SessionMessage(role="assistant", content=resp.answer, ts=None))
    # 防止无限增长
    if len(hist) > 40:
        del hist[:-40]
    return resp


@app.post("/v1/events/analyze", response_model=PeriodicDefectAnalysis)
def analyze_event(event: AnomalyEvent) -> PeriodicDefectAnalysis:
    """事件分析入口：在已有 AnomalyEvent 上直接跑 Skill（便于联调）。"""
    return run_periodic_defect_skill(event)


@app.get("/v1/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return {"session_id": session_id, "messages": [m.model_dump() for m in SESSIONS.get(session_id, [])]}
