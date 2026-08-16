import streamlit as st

from src.agent import FaultRoutingAgent


st.set_page_config(
    page_title="Industrial Fault Routing Agent",
    page_icon="⚙️",
    layout="wide",
)


@st.cache_resource
def get_agent():
    return FaultRoutingAgent()


@st.cache_data
def load_alerts():
    agent = FaultRoutingAgent()
    return agent.load_alerts("data/sample_faults.json")


def action_label(action):
    labels = {
        "immediate_shutdown": "🔴 Immediate Shutdown",
        "scheduled_maintenance": "🟠 Scheduled Maintenance",
        "continue_monitoring": "🟢 Continue Monitoring",
        "escalate_to_specialist": "🟣 Escalate to Specialist",
    }

    return labels.get(action, action)


agent = get_agent()
alerts = load_alerts()


st.title("Industrial Fault Routing Agent")

st.caption(
    "Resolves conflicting diagnostics from an anomaly detector "
    "and a rule-based diagnostic engine."
)


fault_ids = [alert.fault_id for alert in alerts]

selected_fault = st.selectbox(
    "Select fault alert",
    fault_ids,
)

alert = next(
    alert
    for alert in alerts
    if alert.fault_id == selected_fault
)


decision = agent.process_alert(alert)


st.subheader(
    f"{alert.fault_id} — {alert.equipment_id}"
)

meta1, meta2, meta3 = st.columns(3)

meta1.metric(
    "Equipment Type",
    alert.equipment_type.replace("_", " ").title(),
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
    st.subheader("Anomaly Detector")

    st.write(
        f"**Diagnosis:** {alert.anomaly.diagnosis}"
    )

    st.metric(
        "Confidence",
        f"{alert.anomaly.confidence:.0%}",
    )

    st.write(
        f"**Severity:** {alert.anomaly.severity.value.upper()}"
    )

    st.write("**Recent confidence history:**")

    st.line_chart(
        alert.anomaly.confidence_history
    )


with right:
    st.subheader("Rule Engine")

    st.write(
        f"**Diagnosis:** {alert.rule.diagnosis}"
    )

    st.write(
        f"**Fault Code:** "
        f"{alert.rule.fault_code or 'No matching code'}"
    )

    st.write(
        f"**Rule Version:** {alert.rule.rule_version}"
    )

    st.write(
        "**Recommended Action:** "
        f"{action_label(alert.rule.recommended_action.value)}"
    )


st.divider()


st.subheader("Detected Conflict")

if decision.conflicts:
    for conflict in decision.conflicts:
        st.warning(conflict)
else:
    st.success("The diagnostic systems agree.")


st.subheader("Reliability Assessment")

score1, score2 = st.columns(2)

score1.metric(
    "Anomaly Reliability",
    f"{decision.anomaly_reliability:.0%}",
)

score2.metric(
    "Rule Reliability",
    f"{decision.rule_reliability:.0%}",
)


st.divider()


st.subheader("Routing Decision")

st.header(
    action_label(decision.action.value)
)

st.write(
    f"**Winning diagnostic:** "
    f"{decision.winner.value.replace('_', ' ').title()}"
)


st.subheader("Criteria Applied")

for criterion in decision.criteria_applied:
    st.write(
        f"✓ {criterion.replace('_', ' ').title()}"
    )


st.subheader("Decision Reasoning")

for reason in decision.reasons:
    st.write(f"- {reason}")


with st.expander("Audit Details"):
    st.json(
        {
            "fault_id": decision.fault_id,
            "winner": decision.winner.value,
            "action": decision.action.value,
            "conflict_detected": decision.conflict_detected,
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