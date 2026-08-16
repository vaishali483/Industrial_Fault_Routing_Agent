import json
from pathlib import Path

import streamlit as st

from src.agent import FaultRoutingAgent
from src.decision_engine import (
    CLEAR_WIN_MARGIN,
    CONFIDENCE_OSCILLATION_THRESHOLD,
    HIGH_ANOMALY_CONFIDENCE,
    MIN_TRUSTWORTHY_SCORE,
)


st.set_page_config(
    page_title="Industrial Fault Routing Agent",
    page_icon="⚙️",
    layout="wide",
)


def load_alerts(file_path):
    agent = FaultRoutingAgent()
    return agent.load_alerts(file_path)


def action_label(action):
    labels = {
        "immediate_shutdown": "🔴 Immediate Shutdown",
        "scheduled_maintenance": "🟠 Scheduled Maintenance",
        "continue_monitoring": "🟢 Continue Monitoring",
        "escalate_to_specialist": "🟣 Escalate to Specialist",
    }
    return labels.get(action, action)


def source_label(source):
    labels = {
        "anomaly_detector": "Anomaly Detector",
        "rule_engine": "Rule Engine",
        "neither": "Neither — Specialist Review",
    }
    return labels.get(source, source)


def show_decision(alert, decision):
    st.divider()

    st.subheader("Detected Conflict")

    if decision.conflicts:
        for conflict in decision.conflicts:
            st.warning(conflict)
    else:
        st.success("No diagnostic conflict detected.")

    st.subheader("Reliability Assessment")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Anomaly Detector Reliability",
            f"{decision.anomaly_reliability:.0%}",
        )
        st.progress(decision.anomaly_reliability)

    with col2:
        st.metric(
            "Rule Engine Reliability",
            f"{decision.rule_reliability:.0%}",
        )
        st.progress(decision.rule_reliability)

    st.divider()

    st.subheader("Routing Decision")

    st.markdown(
        f"## {action_label(decision.action.value)}"
    )

    st.write(
        f"**Winning diagnostic:** "
        f"{source_label(decision.winner.value)}"
    )

    if decision.rule_stale:
        st.error(
            "Stale rule update detected. "
            "The rule verdict was excluded from decision authority."
        )

    criteria_col, reasoning_col = st.columns([1, 2])

    with criteria_col:
        st.markdown("### Criteria Applied")

        for criterion in decision.criteria_applied:
            st.write(
                f"✓ {criterion.replace('_', ' ').title()}"
            )

    with reasoning_col:
        st.markdown("### Decision Reasoning")

        for reason in decision.reasons:
            st.write(f"- {reason}")

    with st.expander("Full Audit Record"):
        st.json(
            {
                "fault_id": decision.fault_id,
                "winner": decision.winner.value,
                "action": decision.action.value,
                "conflict_detected": (
                    decision.conflict_detected
                ),
                "conflicts": decision.conflicts,
                "rule_stale": decision.rule_stale,
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
            }
        )


def show_audit_log():
    log_path = Path("logs/decisions.jsonl")

    if not log_path.exists():
        st.info(
            "No decisions have been processed yet."
        )
        return

    records = []

    with log_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)

            records.append(
                {
                    "Timestamp": record["timestamp"],
                    "Fault": record["fault_id"],
                    "Winner": record["decision"]["winner"],
                    "Action": record["decision"]["action"],
                    "Anomaly Score": record["decision"][
                        "anomaly_reliability"
                    ],
                    "Rule Score": record["decision"][
                        "rule_reliability"
                    ],
                    "Rule Stale": record["diagnostics"][
                        "rule_engine"
                    ]["stale"],
                }
            )

    if records:
        st.dataframe(
            records[-10:][::-1],
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.title("⚙️ Industrial Fault Routing Agent")

st.write(
    "An auditable decision agent that resolves conflicts "
    "between an ML anomaly detector and a rule-based "
    "diagnostic engine."
)

st.caption(
    "The agent does not permanently trust either diagnostic "
    "source. Reliability is evaluated per fault using "
    "confidence stability, rule freshness, failure history, "
    "known fault coverage, and equipment criticality."
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.header("Demo Mode")

mode = st.sidebar.radio(
    "Choose scenario",
    [
        "Fault Routing",
        "Out-of-Sequence Rule Update",
        "Audit Log",
    ],
)

with st.sidebar.expander("Decision Policy"):
    st.write(
        f"High anomaly confidence: "
        f"{HIGH_ANOMALY_CONFIDENCE:.2f}"
    )

    st.write(
        f"Noise threshold: "
        f"{CONFIDENCE_OSCILLATION_THRESHOLD:.2f}"
    )

    st.write(
        f"Minimum trustworthy score: "
        f"{MIN_TRUSTWORTHY_SCORE:.2f}"
    )

    st.write(
        f"Minimum winning margin: "
        f"{CLEAR_WIN_MARGIN:.2f}"
    )


# ---------------------------------------------------------
# Standard fault routing
# ---------------------------------------------------------

if mode == "Fault Routing":

    alerts = load_alerts(
        "data/sample_faults.json"
    )

    fault_ids = [
        alert.fault_id
        for alert in alerts
    ]

    selected_fault = st.selectbox(
        "Select a fault alert",
        fault_ids,
    )

    alert = next(
        alert
        for alert in alerts
        if alert.fault_id == selected_fault
    )

    st.subheader(
        f"{alert.fault_id} — {alert.equipment_id}"
    )

    meta1, meta2, meta3 = st.columns(3)

    meta1.metric(
        "Equipment Type",
        alert.equipment_type
        .replace("_", " ")
        .title(),
    )

    meta2.metric(
        "Criticality",
        alert.criticality.value.upper(),
    )

    meta3.metric(
        "Previous Similar Failures",
        alert.previous_similar_failures,
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("### Anomaly Detector")

        st.write(
            f"**Diagnosis:** "
            f"{alert.anomaly.diagnosis}"
        )

        st.metric(
            "Confidence",
            f"{alert.anomaly.confidence:.0%}",
        )

        st.write(
            f"**Severity:** "
            f"{alert.anomaly.severity.value.upper()}"
        )

        st.write(
            "**Recent confidence history**"
        )

        st.line_chart(
            alert.anomaly.confidence_history
        )

    with right:
        st.markdown("### Rule Engine")

        st.write(
            f"**Diagnosis:** "
            f"{alert.rule.diagnosis}"
        )

        st.write(
            f"**Fault Code:** "
            f"{alert.rule.fault_code or 'No matching rule'}"
        )

        st.write(
            f"**Rule Version:** "
            f"{alert.rule.rule_version}"
        )

        st.write(
            "**Recommended Action:** "
            f"{action_label(alert.rule.recommended_action.value)}"
        )

    if "decisions" not in st.session_state:
        st.session_state.decisions = {}

    st.divider()

    if st.button(
        "Process Fault Alert",
        type="primary",
        use_container_width=True,
    ):
        agent = FaultRoutingAgent()

        decision = agent.process_alert(
            alert
        )

        st.session_state.decisions[
            alert.fault_id
        ] = decision

    decision = st.session_state.decisions.get(
        alert.fault_id
    )

    if decision:
        show_decision(
            alert,
            decision,
        )
    else:
        st.info(
            "Select Process Fault Alert to run "
            "the routing decision."
        )


# ---------------------------------------------------------
# Required stale-rule failure mode
# ---------------------------------------------------------

elif mode == "Out-of-Sequence Rule Update":

    st.subheader(
        "Out-of-Sequence Rule Engine Update"
    )

    st.write(
        "This scenario demonstrates protection against an older "
        "rule verdict arriving after a newer rule version."
    )

    st.code(
        "Version 12 arrives first\n"
        "        ↓\n"
        "Version 10 arrives later\n"
        "        ↓\n"
        "Version 10 is detected as stale",
        language="text",
    )

    if st.button(
        "Run Rule Update Sequence",
        type="primary",
        use_container_width=True,
    ):

        agent = FaultRoutingAgent()

        alerts = agent.load_alerts(
            "data/rule_update_scenario.json"
        )

        results = []

        for alert in alerts:
            decision = agent.process_alert(
                alert
            )

            results.append(
                {
                    "fault_id": alert.fault_id,
                    "rule_version": (
                        alert.rule.rule_version
                    ),
                    "rule_diagnosis": (
                        alert.rule.diagnosis
                    ),
                    "rule_stale": (
                        decision.rule_stale
                    ),
                    "rule_reliability": (
                        decision.rule_reliability
                    ),
                    "winner": (
                        decision.winner.value
                    ),
                    "action": (
                        decision.action.value
                    ),
                    "reasons": (
                        decision.reasons
                    ),
                }
            )

        st.session_state.rule_results = results

    results = st.session_state.get(
        "rule_results"
    )

    if results:

        for index, result in enumerate(results):

            st.divider()

            st.markdown(
                f"### Arrival {index + 1}: "
                f"Rule Version "
                f"{result['rule_version']}"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Rule Version",
                result["rule_version"],
            )

            col2.metric(
                "Rule Reliability",
                f"{result['rule_reliability']:.0%}",
            )

            col3.metric(
                "Stale Verdict",
                "YES"
                if result["rule_stale"]
                else "NO",
            )

            st.write(
                f"**Rule diagnosis:** "
                f"{result['rule_diagnosis']}"
            )

            st.write(
                f"**Winner:** "
                f"{source_label(result['winner'])}"
            )

            st.write(
                f"**Final action:** "
                f"{action_label(result['action'])}"
            )

            if result["rule_stale"]:
                st.error(
                    "Older rule version detected. "
                    "Its reliability is set to zero "
                    "and it cannot override the newer verdict."
                )

            with st.expander(
                "Decision reasoning"
            ):
                for reason in result["reasons"]:
                    st.write(f"- {reason}")


# ---------------------------------------------------------
# Audit history
# ---------------------------------------------------------

else:

    st.subheader("Auditable Decision History")

    st.write(
        "Each processed alert is appended as a structured "
        "JSONL record containing inputs, conflicts, criteria, "
        "reliability scores, winner, action, and reasoning."
    )

    show_audit_log()