from __future__ import annotations

import hashlib

import numpy as np

from steel_platform.schemas.defects import DefectSample
from steel_platform.schemas.events import EventWindowSummary


def _pseudo_embedding(sample: DefectSample, dim: int = 32) -> list[float]:
    """无真实 embedding 时用确定性伪向量，保证流程可跑通。"""
    h = hashlib.sha256(
        f"{sample.defect_class}|{sample.batch_id}|{sample.position_mm:.4f}".encode()
    ).digest()
    vals = []
    for i in range(dim):
        b = h[i % len(h)]
        vals.append((b / 255.0) * 2 - 1)
    return vals


def build_event_window_summary(samples: list[DefectSample]) -> EventWindowSummary:
    """
    Skill 事件窗口：多缺陷 embedding 按置信度加权平均 → event_embedding。
    """
    if not samples:
        raise ValueError("samples 不能为空")

    first = samples[0]
    dim = 32
    vecs: list[np.ndarray] = []
    weights: list[float] = []
    for s in samples:
        raw = s.embedding if s.embedding is not None else _pseudo_embedding(s, dim=dim)
        if len(raw) != dim:
            # 维度不一致时截断或填充到 dim
            arr = np.zeros(dim, dtype=np.float64)
            n = min(dim, len(raw))
            arr[:n] = np.array(raw[:n], dtype=np.float64)
            raw_vec = arr
        else:
            raw_vec = np.array(raw, dtype=np.float64)
        vecs.append(raw_vec)
        weights.append(max(float(s.confidence), 1e-6))

    w = np.array(weights, dtype=np.float64)
    w = w / w.sum()
    stacked = np.stack(vecs, axis=0)
    event_emb = (stacked * w[:, None]).sum(axis=0)
    # L2 归一化，便于与“相似案例”余弦风格对比（此处仅占位）
    norm = np.linalg.norm(event_emb)
    if norm > 1e-9:
        event_emb = event_emb / norm

    ts = [s.timestamp for s in samples]
    positions = [float(s.position_mm) for s in samples]

    return EventWindowSummary(
        defect_class=first.defect_class,
        line_id=first.line_id,
        camera_id=first.camera_id,
        window_start=min(ts),
        window_end=max(ts),
        sample_count=len(samples),
        event_embedding=[float(x) for x in event_emb.tolist()],
        positions_mm=positions,
    )
