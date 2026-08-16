import json

from src.decision_engine import DecisionEngine
from src.models import (
    Action,
    AnomalyDiagnostic,
    Criticality,
    FaultAlert,
    RuleDiagnostic,
    Severity,
)


class FaultRoutingAgent:
    def __init__(self):
        self.decision_engine = DecisionEngine()

    def process_alert(self, alert: FaultAlert):
        return self.decision_engine.decide(alert)

    def load_alerts(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as file:
            raw_alerts = json.load(file)

        return [
            self._parse_alert(data)
            for data in raw_alerts
        ]

    def _parse_alert(self, data):
        return FaultAlert(
            fault_id=data["fault_id"],
            equipment_id=data["equipment_id"],
            equipment_type=data["equipment_type"],
            criticality=Criticality(data["criticality"]),

            anomaly=AnomalyDiagnostic(
                diagnosis=data["anomaly"]["diagnosis"],
                confidence=data["anomaly"]["confidence"],
                severity=Severity(data["anomaly"]["severity"]),
                confidence_history=data["anomaly"].get(
                    "confidence_history",
                    [],
                ),
            ),

            rule=RuleDiagnostic(
                diagnosis=data["rule"]["diagnosis"],
                fault_code=data["rule"].get("fault_code"),
                recommended_action=Action(
                    data["rule"]["recommended_action"]
                ),
                rule_version=data["rule"]["rule_version"],
            ),

            previous_similar_failures=data.get(
                "previous_similar_failures",
                0,
            ),
        )