from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from steel_platform.schemas.defects import ChatResponse
from steel_platform.tools.mock_tools import (
    tool_alerts_unhandled,
    tool_knowledge_rag,
    tool_production_stats,
    tool_target_query,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time_window(question: str) -> tuple[datetime, datetime]:
    """极简时间解析：满足实习演示；生产环境应接 NLP/规则库。"""
    q = question.strip()
    now = _now()
    if "今天上午" in q or ("上午" in q and "今天" in q):
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=12, minute=0, second=0, microsecond=0)
        return start, end
    if "今天" in q:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now
    m = re.search(r"L(\d+)", q, re.I)
    # 默认：过去 8 小时
    return now - timedelta(hours=8), now


def _extract_line_id(question: str) -> str | None:
    m = re.search(r"L(\d+)", question, re.I)
    if m:
        return f"L{m.group(1)}"
    return None


def classify_intent(question: str) -> str:
    q = question.strip()
    if any(k in q for k in ("过钢", "合格率", "产量", "质量统计", "今天上午")):
        return "QueryProductionStatus"
    if any(k in q for k in ("目标", "达成", "完成率")):
        return "CheckTargetAchievement"
    if any(k in q for k in ("周期性", "周期缺陷", "重复出现", "等间距")):
        return "AnalyzeDefectPattern"
    if any(k in q for k in ("先检查", "排查", "怎么处理", "设备", "告警")):
        return "TroubleshootingGuide"
    return "General"


def run_chat(session_id: str, question: str) -> ChatResponse:
    """
    智能问答入口（流程 B 骨架）：
    意图识别 → 时间/产线实体粗解析 → 工具调用(Mock) → 模板化自然语言总结。
    """
    intent = classify_intent(question)
    trace: list[dict[str, Any]] = []
    line_id = _extract_line_id(question)

    if intent == "QueryProductionStatus":
        start, end = _parse_time_window(question)
        stats = tool_production_stats(line_id, start, end)
        trace.append(stats)
        answer = (
            f"【生产状态摘要】产线 {stats['line_id']}，窗口 {stats['window']['start']} ~ "
            f"{stats['window']['end']}：过钢量约 {stats['throughput_tons']} 吨，"
            f"合格率 {stats['yield_rate']*100:.2f}%，缺陷数 {stats['defect_count']}。"
            f"（{stats['note']}）"
        )
        return ChatResponse(session_id=session_id, answer=answer, intent=intent, tool_trace=trace)

    if intent == "CheckTargetAchievement":
        day = _now()
        tgt = tool_target_query(day)
        trace.append(tgt)
        stats = tool_production_stats(line_id, day.replace(hour=0, minute=0, second=0), _now())
        trace.append(stats)
        ok_throughput = stats["throughput_tons"] >= tgt["daily_throughput_target_tons"] * 0.95
        ok_yield = stats["yield_rate"] >= tgt["daily_yield_target"] * 0.995
        verdict = "基本达到当日目标区间" if ok_throughput and ok_yield else "未完全达到目标，请关注缺陷与设备状态"
        answer = (
            f"【目标核查】{tgt['day']} 目标产能 {tgt['daily_throughput_target_tons']} 吨、"
            f"目标合格率 {tgt['daily_yield_target']*100:.2f}%。"
            f"当前统计过钢 {stats['throughput_tons']} 吨、合格率 {stats['yield_rate']*100:.2f}%。"
            f"结论：{verdict}。（对比逻辑在后端代码完成，非模型臆测。）"
        )
        return ChatResponse(session_id=session_id, answer=answer, intent=intent, tool_trace=trace)

    if intent == "AnalyzeDefectPattern":
        trace.append({"note": "周期性深度分析由事件入口触发 Skill，见 POST /v1/defects/ingest"})
        answer = (
            "【缺陷模式分析】周期性判定需要连续缺陷位置与时间窗口数据。"
            "请将产线检测结果推送至 /v1/defects/ingest；当事件规则触发时，"
            "系统会自动执行周期性缺陷 Skill（规则层周期评分 + 相似案例 + 知识库建议）。"
            "当前问答通道仅作流程说明。"
        )
        return ChatResponse(session_id=session_id, answer=answer, intent=intent, tool_trace=trace)

    if intent == "TroubleshootingGuide":
        rag = tool_knowledge_rag(question, defect_class=None)
        trace.append(rag)
        parts = [f"【{d['title']}】{d['snippet']}" for d in rag.get("docs", [])]
        answer = "根据知识库检索（Mock），建议优先关注：\n" + "\n".join(parts)
        return ChatResponse(session_id=session_id, answer=answer, intent=intent, tool_trace=trace)

    # General
    alerts = tool_alerts_unhandled(line_id)
    trace.append(alerts)
    answer = (
        "我先把当前未处理告警列表拉取供参考："
        + str(alerts.get("items", []))
        + "。如需质量统计请直接问「今天上午过钢质量怎么样」；"
        "如需周期性分析请走缺陷推送接口触发事件链。"
    )
    return ChatResponse(session_id=session_id, answer=answer, intent="General", tool_trace=trace)
