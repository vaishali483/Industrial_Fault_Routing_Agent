from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Criticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Action(str, Enum):
    SHUTDOWN = "immediate_shutdown"
    MAINTENANCE = "scheduled_maintenance"
    MONITOR = "continue_monitoring"
    ESCALATE = "escalate_to_specialist"


class DiagnosticSource(str, Enum):
    ANOMALY = "anomaly_detector"
    RULE = "rule_engine"
    NEITHER = "neither"


@dataclass
class AnomalyDiagnostic:
    diagnosis: str
    confidence: float
    severity: Severity

    # Recent confidence values allow us to detect oscillation/noise.
    confidence_history: List[float] = field(default_factory=list)


@dataclass
class RuleDiagnostic:
    diagnosis: str
    fault_code: Optional[str]
    recommended_action: Action

    # Used to detect stale/out-of-order rule updates.
    rule_version: int


@dataclass
class FaultAlert:
    fault_id: str
    equipment_id: str
    equipment_type: str
    criticality: Criticality

    anomaly: AnomalyDiagnostic
    rule: RuleDiagnostic

    previous_similar_failures: int = 0


@dataclass
class Decision:
    fault_id: str
    winner: DiagnosticSource
    action: Action

    conflict_detected: bool
    conflicts: List[str]

    anomaly_reliability: float
    rule_reliability: float

    criteria_applied: List[str]
    reasons: List[str]

    rule_stale: bool = False