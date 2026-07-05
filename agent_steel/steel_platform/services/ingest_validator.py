from __future__ import annotations

from steel_platform.schemas.defects import DefectIngestPayload, DefectSample, ValidationResult


def validate_defect_payload(payload: DefectIngestPayload) -> ValidationResult:
    """
    数据校验与触发前置：确保含缺陷类别、批次号等核心字段；
    通过后由调用方触发周期性判断 / 事件规则（本函数只做校验）。
    """
    errors: list[str] = []
    normalized: list[DefectSample] = []

    if not payload.samples:
        errors.append("samples 不能为空")
        return ValidationResult(ok=False, errors=errors)

    for i, s in enumerate(payload.samples):
        if not s.defect_class or not s.defect_class.strip():
            errors.append(f"样本 {i}: defect_class 缺失")
        if not s.batch_id or not s.batch_id.strip():
            errors.append(f"样本 {i}: batch_id 缺失")
        if not s.line_id or not s.line_id.strip():
            errors.append(f"样本 {i}: line_id 缺失")
        if not s.camera_id or not s.camera_id.strip():
            errors.append(f"样本 {i}: camera_id 缺失")
        if s.confidence < 0 or s.confidence > 1:
            errors.append(f"样本 {i}: confidence 需在 [0,1]")

    if errors:
        return ValidationResult(ok=False, errors=errors)

    normalized = list(payload.samples)
    return ValidationResult(ok=True, errors=[], normalized_samples=normalized)
