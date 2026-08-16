import json
from datetime import datetime, timezone
from pathlib import Path

from src.models import Decision, FaultAlert


class AuditLogger:
    def __init__(self, log_path: str = "logs/decisions.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, alert: FaultAlert, decision: Decision) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fault_id": alert.fault_id,
            "equipment": {
                "equipment_id": alert.equipment_id,
                "equipment_type": alert.equipment_type,
                "criticality": alert.criticality.value,
                "previous_similar_failures": (
                    alert.previous_similar_failures
                ),
            },
            "diagnostics": {
                "anomaly_detector": {
                    "diagnosis": alert.anomaly.diagnosis,
                    "confidence": alert.anomaly.confidence,
                    "severity": alert.anomaly.severity.value,
                    "confidence_history": (
                        alert.anomaly.confidence_history
                    ),
                },
                "rule_engine": {
                    "diagnosis": alert.rule.diagnosis,
                    "fault_code": alert.rule.fault_code,
                    "recommended_action": (
                        alert.rule.recommended_action.value
                    ),
                    "rule_version": alert.rule.rule_version,
                    "stale": decision.rule_stale,
                },
            },
            "conflict": {
                "detected": decision.conflict_detected,
                "details": decision.conflicts,
            },
            "decision": {
                "winner": decision.winner.value,
                "action": decision.action.value,
                "anomaly_reliability": (
                    decision.anomaly_reliability
                ),
                "rule_reliability": (
                    decision.rule_reliability
                ),
                "criteria_applied": (
                    decision.criteria_applied
                ),
                "reasoning": decision.reasons,
            },
        }

        with self.log_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(json.dumps(record) + "\n")