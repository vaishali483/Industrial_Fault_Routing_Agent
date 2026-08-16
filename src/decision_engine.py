from statistics import pstdev
from typing import List, Tuple

from src.models import (
    Action,
    Criticality,
    DiagnosticSource,
    FaultAlert,
    Severity,
    Decision,
)


HIGH_ANOMALY_CONFIDENCE = 0.85
CONFIDENCE_OSCILLATION_THRESHOLD = 0.20
CLEAR_WIN_MARGIN = 0.15
MIN_TRUSTWORTHY_SCORE = 0.60


class DecisionEngine:
    """
    Resolves conflicts between the anomaly detector and rule engine.

    The engine does not permanently trust either source.
    It calculates a context-dependent reliability score for each source
    and records the criteria used to reach the final decision.
    """

    def __init__(self):
        # Tracks the newest rule version observed for each equipment/fault-code pair.
        self.latest_rule_versions = {}

    def decide(self, alert: FaultAlert) -> Decision:
        criteria_applied: List[str] = []
        reasons: List[str] = []

        # ---------------------------------------------------------
        # 1. Detect stale / out-of-order rule updates
        # ---------------------------------------------------------

        rule_stale = self._is_rule_stale(alert)

        if rule_stale:
            criteria_applied.append("rule_version_freshness")
            reasons.append(
                f"Rule version {alert.rule.rule_version} is older than the "
                "latest rule version already observed for this equipment."
            )

        # ---------------------------------------------------------
        # 2. Detect anomaly confidence oscillation
        # ---------------------------------------------------------

        anomaly_noisy = self._is_anomaly_noisy(
            alert.anomaly.confidence_history
        )

        criteria_applied.append("anomaly_confidence")

        if anomaly_noisy:
            criteria_applied.append("confidence_stability")
            reasons.append(
                "Recent anomaly confidence values oscillate significantly, "
                "reducing trust in the anomaly detector."
            )
        else:
            criteria_applied.append("confidence_stability")
            reasons.append(
                "Recent anomaly confidence values are stable."
            )

        # ---------------------------------------------------------
        # 3. Calculate reliability scores
        # ---------------------------------------------------------

        anomaly_score = self._score_anomaly(
            alert,
            anomaly_noisy,
            criteria_applied,
            reasons,
        )

        rule_score = self._score_rule(
            alert,
            rule_stale,
            criteria_applied,
            reasons,
        )

        # ---------------------------------------------------------
        # 4. Determine what action the anomaly detector implies
        # ---------------------------------------------------------

        anomaly_action = self._anomaly_action(alert)

        # ---------------------------------------------------------
        # 5. Identify specific disagreements
        # ---------------------------------------------------------

        conflicts = self._detect_conflicts(
            alert,
            anomaly_action,
        )

        conflict_detected = len(conflicts) > 0

        # ---------------------------------------------------------
        # 6. Decide which diagnostic wins
        # ---------------------------------------------------------

        score_difference = abs(anomaly_score - rule_score)
        highest_score = max(anomaly_score, rule_score)

        if highest_score < MIN_TRUSTWORTHY_SCORE:
            winner = DiagnosticSource.NEITHER
            action = Action.ESCALATE

            reasons.append(
                f"Neither diagnostic reaches the minimum trustworthy score "
                f"of {MIN_TRUSTWORTHY_SCORE:.2f}; specialist review is required."
            )

        elif score_difference < CLEAR_WIN_MARGIN:
            winner = DiagnosticSource.NEITHER
            action = Action.ESCALATE

            reasons.append(
                f"Reliability scores are too close "
                f"({anomaly_score:.2f} vs {rule_score:.2f}). "
                "The evidence is not strong enough to safely prefer one source."
            )

        elif anomaly_score > rule_score:
            winner = DiagnosticSource.ANOMALY
            action = anomaly_action

            reasons.append(
                f"Anomaly detector wins with reliability "
                f"{anomaly_score:.2f} versus rule engine {rule_score:.2f}."
            )

        else:
            winner = DiagnosticSource.RULE
            action = alert.rule.recommended_action

            reasons.append(
                f"Rule engine wins with reliability "
                f"{rule_score:.2f} versus anomaly detector {anomaly_score:.2f}."
            )

        # ---------------------------------------------------------
        # 7. Record equipment criticality / risk asymmetry
        # ---------------------------------------------------------

        criteria_applied.append("equipment_criticality")

        if alert.criticality == Criticality.HIGH:
            reasons.append(
                "Equipment is high criticality, so the cost of missing a "
                "real failure is treated as high."
            )

        return Decision(
            fault_id=alert.fault_id,
            winner=winner,
            action=action,
            conflict_detected=conflict_detected,
            conflicts=conflicts,
            anomaly_reliability=round(anomaly_score, 2),
            rule_reliability=round(rule_score, 2),
            criteria_applied=list(dict.fromkeys(criteria_applied)),
            reasons=reasons,
            rule_stale=rule_stale,
        )

    # =============================================================
    # Reliability scoring
    # =============================================================

    def _score_anomaly(
        self,
        alert: FaultAlert,
        noisy: bool,
        criteria: List[str],
        reasons: List[str],
    ) -> float:

        score = alert.anomaly.confidence

        if alert.anomaly.confidence >= HIGH_ANOMALY_CONFIDENCE:
            reasons.append(
                f"Anomaly confidence {alert.anomaly.confidence:.2f} "
                f"exceeds the high-confidence threshold "
                f"of {HIGH_ANOMALY_CONFIDENCE:.2f}."
            )

        if noisy:
            score -= 0.40

        if alert.previous_similar_failures > 0:
            criteria.append("failure_history")

            failure_bonus = min(
                alert.previous_similar_failures * 0.05,
                0.15,
            )

            score += failure_bonus

            reasons.append(
                f"{alert.previous_similar_failures} similar previous "
                "failure(s) increase confidence that the anomaly is genuine."
            )

        return self._clamp(score)

    def _score_rule(
        self,
        alert: FaultAlert,
        stale: bool,
        criteria: List[str],
        reasons: List[str],
    ) -> float:

        # Rule engines are relatively precise when a known rule matches.
        score = 0.55

        criteria.append("known_fault_rule")

        if alert.rule.fault_code:
            score += 0.20

            reasons.append(
                f"Rule engine matched known fault code "
                f"{alert.rule.fault_code}."
            )

        else:
            score -= 0.25

            reasons.append(
                "Rule engine has no matching fault code, which lowers "
                "confidence in its verdict for a potentially novel failure."
            )

        criteria.append("rule_version_freshness")

        if stale:
            reasons.append(
                "The rule-engine verdict is stale and is excluded from "
                "decision authority."
            )
            return 0.0

        score += 0.05

        return self._clamp(score)

    # =============================================================
    # Noise detection
    # =============================================================

    def _is_anomaly_noisy(self, history: List[float]) -> bool:
        if len(history) < 3:
            return False

        deviation = pstdev(history)

        return deviation > CONFIDENCE_OSCILLATION_THRESHOLD

    # =============================================================
    # Rule version tracking
    # =============================================================

    def _is_rule_stale(self, alert: FaultAlert) -> bool:
        key = (
            alert.equipment_id,
            alert.rule.fault_code or "__no_fault_code__",
        )

        latest_version = self.latest_rule_versions.get(key)

        if latest_version is None:
            self.latest_rule_versions[key] = alert.rule.rule_version
            return False

        if alert.rule.rule_version < latest_version:
            return True

        if alert.rule.rule_version > latest_version:
            self.latest_rule_versions[key] = alert.rule.rule_version

        return False

    # =============================================================
    # Conflict detection
    # =============================================================

    def _detect_conflicts(
        self,
        alert: FaultAlert,
        anomaly_action: Action,
    ) -> List[str]:

        conflicts = []

        if (
            alert.anomaly.diagnosis.strip().lower()
            != alert.rule.diagnosis.strip().lower()
        ):
            conflicts.append(
                "Root-cause conflict: anomaly detector reports "
                f"'{alert.anomaly.diagnosis}', while the rule engine reports "
                f"'{alert.rule.diagnosis}'."
            )

        if anomaly_action != alert.rule.recommended_action:
            conflicts.append(
                "Action conflict: anomaly evidence suggests "
                f"'{anomaly_action.value}', while the rule engine recommends "
                f"'{alert.rule.recommended_action.value}'."
            )

        return conflicts

    # =============================================================
    # Convert anomaly severity into operational action
    # =============================================================

    def _anomaly_action(self, alert: FaultAlert) -> Action:

        severity = alert.anomaly.severity
        confidence = alert.anomaly.confidence

        if severity == Severity.CRITICAL:
            if (
                alert.criticality == Criticality.HIGH
                or confidence >= 0.90
            ):
                return Action.SHUTDOWN

            return Action.MAINTENANCE

        if severity == Severity.HIGH:
            if (
                alert.criticality == Criticality.HIGH
                and confidence >= HIGH_ANOMALY_CONFIDENCE
            ):
                return Action.SHUTDOWN

            return Action.MAINTENANCE

        if severity == Severity.MEDIUM:
            if confidence >= 0.70:
                return Action.MAINTENANCE

            return Action.MONITOR

        return Action.MONITOR

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))