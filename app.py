from src.agent import FaultRoutingAgent


def main():
    agent = FaultRoutingAgent()

    alerts = agent.load_alerts(
        "data/sample_faults.json"
    )

    for alert in alerts:
        decision = agent.process_alert(alert)

        print("\n" + "=" * 70)
        print(f"FAULT: {alert.fault_id}")
        print(f"EQUIPMENT: {alert.equipment_id}")
        print("=" * 70)

        print("\nDIAGNOSTICS")
        print(
            f"Anomaly : {alert.anomaly.diagnosis} "
            f"(confidence={alert.anomaly.confidence:.2f})"
        )
        print(
            f"Rule    : {alert.rule.diagnosis}"
        )

        print("\nCONFLICTS")

        if decision.conflicts:
            for conflict in decision.conflicts:
                print(f"- {conflict}")
        else:
            print("- No conflict detected")

        print("\nRELIABILITY")
        print(
            f"Anomaly detector : "
            f"{decision.anomaly_reliability:.2f}"
        )
        print(
            f"Rule engine      : "
            f"{decision.rule_reliability:.2f}"
        )

        print("\nDECISION")
        print(f"Winner : {decision.winner.value}")
        print(f"Action : {decision.action.value}")

        print("\nREASONING")

        for reason in decision.reasons:
            print(f"- {reason}")

    print("\n\n" + "#" * 70)
    print("OUT-OF-SEQUENCE RULE UPDATE SCENARIO")
    print("#" * 70)

    rule_update_alerts = agent.load_alerts(
        "data/rule_update_scenario.json"
    )

    for alert in rule_update_alerts:
        decision = agent.process_alert(alert)

        print("\n" + "=" * 70)
        print(f"FAULT: {alert.fault_id}")
        print(f"EQUIPMENT: {alert.equipment_id}")
        print(f"RULE VERSION: {alert.rule.rule_version}")
        print("=" * 70)

        print(f"Rule stale: {decision.rule_stale}")
        print(
            f"Anomaly reliability: "
            f"{decision.anomaly_reliability:.2f}"
        )
        print(
            f"Rule reliability: "
            f"{decision.rule_reliability:.2f}"
        )

        print(f"Winner: {decision.winner.value}")
        print(f"Action: {decision.action.value}")

        print("\nReasoning:")

        for reason in decision.reasons:
            print(f"- {reason}")


if __name__ == "__main__":
    main()