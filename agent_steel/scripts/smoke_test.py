from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from steel_platform.schemas.defects import DefectIngestPayload, DefectSample
from steel_platform.services.event_engine import EventRuleEngine
from steel_platform.services.ingest_validator import validate_defect_payload
from steel_platform.skills.periodic_defect import run_periodic_defect_skill


def main() -> None:
    now = datetime.now()
    samples = [
        DefectSample(
            defect_class="scratch",
            batch_id="B1",
            timestamp=now + timedelta(seconds=i),
            position_mm=100.0 + i * 50.0,
            line_id="L2",
            camera_id="C1",
            embedding=[0.1] * 32,
            confidence=0.9,
        )
        for i in range(4)
    ]
    vr = validate_defect_payload(DefectIngestPayload(samples=samples))
    assert vr.ok
    event = EventRuleEngine(consecutive_n=3).evaluate(vr.normalized_samples)
    assert event is not None
    analysis = run_periodic_defect_skill(event)
    assert analysis.periodicity_conclusion in ("强周期", "弱周期", "非周期", "无法判定")
    print("smoke ok", event.event_id, analysis.headline)


if __name__ == "__main__":
    main()
