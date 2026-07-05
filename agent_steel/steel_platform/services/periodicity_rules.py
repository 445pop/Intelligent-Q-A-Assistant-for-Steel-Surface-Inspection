from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PeriodicityAssessment:
    """确定性规则层输出，避免交给模型推断。"""

    conclusion: str  # 强周期 / 弱周期 / 非周期 / 无法判定
    main_period_mm: float | None
    spacing_cv: float | None
    evidence: str


def assess_periodicity(positions_mm: list[float], min_points: int = 4) -> PeriodicityAssessment:
    """
    基于沿轧向位置序列：一阶间距 → 主周期估计（中位数）→ 间距 CV。
    与 agent.txt / skill 思路一致：强周期 CV 较小；样本不足则无法判定。
    """
    xs = sorted(float(x) for x in positions_mm)
    if len(xs) < 2:
        return PeriodicityAssessment(
            conclusion="无法判定",
            main_period_mm=None,
            spacing_cv=None,
            evidence="有效位置点不足，无法计算间距。",
        )

    deltas = np.diff(np.array(xs, dtype=np.float64))
    if deltas.size == 0:
        return PeriodicityAssessment(
            conclusion="无法判定",
            main_period_mm=None,
            spacing_cv=None,
            evidence="无相邻间距。",
        )

    median_t = float(np.median(deltas))
    mean_t = float(np.mean(deltas))
    std_t = float(np.std(deltas))
    cv = float(std_t / mean_t) if mean_t > 1e-6 else None

    if len(xs) < min_points:
        return PeriodicityAssessment(
            conclusion="无法判定",
            main_period_mm=median_t if median_t > 0 else None,
            spacing_cv=cv,
            evidence=f"样本点仅 {len(xs)} 个，建议不少于 {min_points} 个再判强周期。",
        )

    if cv is None:
        return PeriodicityAssessment(
            conclusion="无法判定",
            main_period_mm=None,
            spacing_cv=None,
            evidence="间距均值过小，数值不稳定。",
        )

    # 工程经验阈值（可调）：与 skill 中 0.05–0.25 量级一致
    if cv <= 0.22 and median_t > 0:
        conclusion = "强周期"
        evidence = f"间距中位数约 {median_t:.2f} mm，变异系数 CV={cv:.3f}，主间距较稳定。"
    elif cv <= 0.45 and median_t > 0:
        conclusion = "弱周期"
        evidence = f"间距中位数约 {median_t:.2f} mm，CV={cv:.3f}，存在准周期但波动较大。"
    else:
        conclusion = "非周期"
        evidence = f"间距分布分散，CV={cv:.3f}，未形成稳定主周期。"

    return PeriodicityAssessment(
        conclusion=conclusion,
        main_period_mm=median_t if median_t > 0 else None,
        spacing_cv=cv,
        evidence=evidence,
    )
