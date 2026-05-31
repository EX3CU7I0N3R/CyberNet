from __future__ import annotations


RECOMMENDATIONS_BY_HYPOTHESIS = {
    "beaconing": [
        "Review endpoint telemetry",
        "Identify initiating process",
        "Investigate destination",
        "Check EDR alerts",
    ],
    "persistent_tls": [
        "Inspect destination ownership",
        "Review process activity",
        "Verify application legitimacy",
    ],
    "port_scan": [
        "Review source host activity",
        "Inspect authentication logs",
        "Validate intended behavior",
    ],
    "host_sweep": [
        "Review source host activity",
        "Inspect authentication logs",
        "Validate intended behavior",
    ],
}


class RecommendationEngine:
    def recommendations_for(self, hypotheses: list) -> list[str]:
        recommendations = []
        for hypothesis in hypotheses:
            for recommendation in RECOMMENDATIONS_BY_HYPOTHESIS.get(hypothesis.hypothesis_type, []):
                if recommendation not in recommendations:
                    recommendations.append(recommendation)

        if recommendations:
            return recommendations

        return [
            "Review endpoint telemetry",
            "Validate expected business activity",
            "Correlate with authentication and EDR data",
        ]
