from src.decision_engine import DecisionEngine
from src.models import (
    Action,
    AnomalyDiagnostic,
    Criticality,
    DiagnosticSource,
    FaultAlert,
    RuleDiagnostic,
    Severity,
)


def make_alert(
    fault_id="TEST-001",
    equipment_id="TEST-MACHINE",
    criticality=Criticality.MEDIUM,
    anomaly_diagnosis="abnormal vibration",
    anomaly_confidence=0.90,
    anomaly_severity=Severity.HIGH,
    confidence_history=None,
    rule_diagnosis="known vibration condition",
    fault_code="VIB-001",
    rule_action=Action.MONITOR,
    rule_version=1,
    previous_failures=0,
):
    if confidence_history is None:
        confidence_history = [0.87, 0.88, 0.89, 0.90]

    return FaultAlert(
        fault_id=fault_id,
        equipment_id=equipment_id,
        equipment_type="test_equipment",
        criticality=criticality,
        anomaly=AnomalyDiagnostic(
            diagnosis=anomaly_diagnosis,
            confidence=anomaly_confidence,
            severity=anomaly_severity,
            confidence_history=confidence_history,
        ),
        rule=RuleDiagnostic(
            diagnosis=rule_diagnosis,
            fault_code=fault_code,
            recommended_action=rule_action,
            rule_version=rule_version,
        ),
        previous_similar_failures=previous_failures,
    )


def test_high_confidence_critical_anomaly_causes_shutdown():
    engine = DecisionEngine()

    alert = make_alert(
        criticality=Criticality.HIGH,
        anomaly_confidence=0.95,
        anomaly_severity=Severity.CRITICAL,
        previous_failures=2,
        rule_action=Action.MONITOR,
    )

    decision = engine.decide(alert)

    assert decision.winner == DiagnosticSource.ANOMALY
    assert decision.action == Action.SHUTDOWN


def test_noisy_anomaly_allows_rule_engine_to_win():
    engine = DecisionEngine()

    alert = make_alert(
        criticality=Criticality.LOW,
        anomaly_confidence=0.91,
        anomaly_severity=Severity.HIGH,
        confidence_history=[0.91, 0.30, 0.88, 0.29, 0.92],
        rule_action=Action.MONITOR,
    )

    decision = engine.decide(alert)

    assert decision.winner == DiagnosticSource.RULE
    assert decision.action == Action.MONITOR
    assert decision.rule_reliability > decision.anomaly_reliability


def test_close_scores_escalate_to_specialist():
    engine = DecisionEngine()

    alert = make_alert(
        anomaly_confidence=0.74,
        anomaly_severity=Severity.MEDIUM,
        previous_failures=1,
        rule_action=Action.MAINTENANCE,
    )

    decision = engine.decide(alert)

    assert decision.winner == DiagnosticSource.NEITHER
    assert decision.action == Action.ESCALATE


def test_rule_engine_can_route_to_scheduled_maintenance():
    engine = DecisionEngine()

    alert = make_alert(
        criticality=Criticality.LOW,
        anomaly_confidence=0.48,
        anomaly_severity=Severity.LOW,
        confidence_history=[0.44, 0.46, 0.47, 0.48],
        rule_diagnosis="bearing lubrication required",
        fault_code="LUBE-500",
        rule_action=Action.MAINTENANCE,
    )

    decision = engine.decide(alert)

    assert decision.winner == DiagnosticSource.RULE
    assert decision.action == Action.MAINTENANCE


def test_out_of_sequence_rule_update_is_marked_stale():
    engine = DecisionEngine()

    newer_alert = make_alert(
        fault_id="RULE-NEW",
        equipment_id="BOILER-04",
        fault_code="TEMP-301",
        rule_version=12,
        rule_action=Action.MAINTENANCE,
    )

    stale_alert = make_alert(
        fault_id="RULE-OLD",
        equipment_id="BOILER-04",
        fault_code="TEMP-301",
        rule_version=10,
        rule_action=Action.MONITOR,
    )

    first_decision = engine.decide(newer_alert)
    stale_decision = engine.decide(stale_alert)

    assert first_decision.rule_stale is False

    assert stale_decision.rule_stale is True
    assert stale_decision.rule_reliability == 0.0


def test_no_matching_rule_reduces_rule_reliability():
    engine = DecisionEngine()

    alert = make_alert(
        criticality=Criticality.HIGH,
        anomaly_confidence=0.90,
        anomaly_severity=Severity.HIGH,
        rule_diagnosis="no recognised fault condition",
        fault_code=None,
        rule_action=Action.MONITOR,
    )

    decision = engine.decide(alert)

    assert decision.winner == DiagnosticSource.ANOMALY
    assert decision.rule_reliability < decision.anomaly_reliability


def test_low_confidence_sources_do_not_force_a_winner():
    engine = DecisionEngine()

    alert = make_alert(
        anomaly_confidence=0.25,
        anomaly_severity=Severity.LOW,
        confidence_history=[0.20, 0.22, 0.24, 0.25],
        fault_code=None,
        rule_action=Action.MONITOR,
    )

    decision = engine.decide(alert)

    assert decision.winner == DiagnosticSource.NEITHER
    assert decision.action == Action.ESCALATE