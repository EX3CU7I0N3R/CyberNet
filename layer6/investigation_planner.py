from __future__ import annotations


PLAN_BY_HYPOTHESIS = {
    "beaconing": [
        "Review endpoint telemetry for the host during the capture window",
        "Identify the process responsible for the external connection",
        "Review destination ownership and reputation using approved internal sources",
        "Correlate DNS and TLS activity for the destination",
        "Examine the user and process activity timeline around the recurring communications",
    ],
    "persistent_tls": [
        "Inspect destination ownership",
        "Review process activity",
        "Verify application legitimacy",
    ],
    "port_scan": [
        "Review source host activity",
        "Inspect authentication logs",
        "Validate whether the scan pattern was expected administrative behavior",
    ],
    "host_sweep": [
        "Review source host activity",
        "Inspect authentication logs",
        "Validate whether the peer sweep was expected administrative behavior",
    ],
}


class InvestigationPlanner:
    def plan(self, hypotheses: list) -> list[str]:
        ordered_actions = []
        for hypothesis in hypotheses:
            for action in PLAN_BY_HYPOTHESIS.get(hypothesis.hypothesis_type, []):
                if action not in ordered_actions:
                    ordered_actions.append(action)

        if ordered_actions:
            return ordered_actions[:5]

        return [
            "Review endpoint telemetry",
            "Validate expected business activity",
            "Correlate with authentication and EDR data",
        ]
