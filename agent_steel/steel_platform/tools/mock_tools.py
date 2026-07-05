from __future__ import annotations

from datetime import datetime
from typing import Any


def tool_production_stats(line_id: str | None, start: datetime, end: datetime) -> dict[str, Any]:
    """Tool 1：生产质量统计（Mock）。"""
    return {
        "tool": "production_stats",
        "line_id": line_id or "ALL",
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "throughput_tons": 1280.5,
        "yield_rate": 0.982,
        "defect_count": 42,
        "note": "Mock 数据：接 MySQL 后替换实现。",
    }


def tool_target_query(day: datetime) -> dict[str, Any]:
    """Tool 2：目标值查询（Mock）。"""
    return {
        "tool": "target_query",
        "day": day.date().isoformat(),
        "daily_throughput_target_tons": 1500.0,
        "daily_yield_target": 0.985,
        "note": "Mock：来自 Word 目标表解析入库后的占位结果。",
    }


def tool_alerts_unhandled(line_id: str | None) -> dict[str, Any]:
    """Tool 3：未处理缺陷告警（Mock）。"""
    return {
        "tool": "alerts_unhandled",
        "line_id": line_id or "ALL",
        "items": [
            {
                "batch_id": "B-20260514-001",
                "defect_class": "划伤",
                "line_id": "L2",
                "status": "open",
            }
        ],
        "note": "Mock：接告警表后替换。",
    }


def tool_milvus_similar_cases(
    event_embedding: list[float],
    defect_class: str,
    line_id: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """Tool 4：Milvus 相似案例检索（Mock）。"""
    dim = len(event_embedding)
    hits = []
    for i in range(min(top_k, 3)):
        hits.append(
            {
                "case_id": f"HIST-{line_id}-{1000 + i}",
                "score": 0.92 - i * 0.04,
                "periodicity_label": "强周期" if i == 0 else "弱周期",
                "human_conclusion": "导辊磨损相关" if i < 2 else "待确认",
                "summary": "历史卷上同类划伤呈准等间距分布，现场更换导辊后消失。",
            }
        )
    return {
        "tool": "milvus_similar",
        "defect_class": defect_class,
        "line_id": line_id,
        "embedding_dim": dim,
        "hits": hits,
        "note": "Mock：接 Milvus 后替换为真实向量检索。",
    }


def tool_knowledge_rag(query: str, defect_class: str | None = None) -> dict[str, Any]:
    """Tool 5：设备维护知识库检索（Mock）。"""
    q = query.lower()
    docs = []
    if "导辊" in query or "辊" in query or defect_class in ("划伤",):
        docs.append(
            {
                "doc_id": "KB-ROLLER-01",
                "title": "导辊磨损导致表面划伤排查",
                "snippet": "优先检查导辊表面磨损、异物附着、局部凹坑；同步检查张力与辊系对中。",
                "source_priority": "high",
            }
        )
    if "张力" in query:
        docs.append(
            {
                "doc_id": "KB-TENSION-02",
                "title": "张力异常处理规范",
                "snippet": "检查张力设定、活套与传感器；异常波动可能造成间距漂移的伪周期。",
                "source_priority": "high",
            }
        )
    if not docs:
        docs.append(
            {
                "doc_id": "KB-GENERAL",
                "title": "表面缺陷通用排查",
                "snippet": "结合缺陷类别与位置集中度，逐项排除辊系、夹送与清洁系统。",
                "source_priority": "medium",
            }
        )
    return {"tool": "knowledge_rag", "query": query, "docs": docs}
