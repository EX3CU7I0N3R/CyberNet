from __future__ import annotations


class AssessmentEngine:
    def assess(self, hypotheses: list) -> str:
        if not hypotheses:
            return "Observed activity suggests behavior that warrants analyst review."

        statements = []
        hypothesis_types = {hypothesis.hypothesis_type for hypothesis in hypotheses}
        primary = self._primary_hypothesis(hypotheses)

        if "beaconing" in hypothesis_types:
            statements.append("Observed activity is consistent with command-and-control beaconing.")
        if "persistent_tls" in hypothesis_types:
            statements.append("Observed behavior indicates persistent encrypted communication.")
        if {"port_scan", "host_sweep"} & hypothesis_types:
            statements.append("Observed behavior suggests reconnaissance activity.")
        if primary and {"persistence", "periodicity", "exclusive_destination"} & set(primary.supporting_evidence):
            statements.append("The behavior exhibits persistence, timing regularity, and destination exclusivity.")

        statements.append("Additional endpoint investigation is recommended before concluding malicious activity.")
        return " ".join(dict.fromkeys(statements))

    def negative_findings(self, hypotheses: list) -> list[str]:
        hypothesis_types = {hypothesis.hypothesis_type for hypothesis in hypotheses}
        findings = []

        if not {"port_scan", "host_sweep"} & hypothesis_types:
            findings.append("No Layer 5 reconnaissance hypothesis was generated for this host during the capture.")
        if "persistent_tls" not in hypothesis_types:
            findings.append("No separate persistent encrypted-channel hypothesis was generated beyond the observed beaconing behavior.")

        if not findings:
            findings.append("No additional negative findings were identified from the currently implemented Layer 5 hypothesis set.")
        return findings

    def _primary_hypothesis(self, hypotheses: list):
        primary = [hypothesis for hypothesis in hypotheses if hypothesis.finding_tier == "PRIMARY"]
        if primary:
            return sorted(primary, key=lambda hypothesis: hypothesis.confidence, reverse=True)[0]
        return sorted(hypotheses, key=lambda hypothesis: hypothesis.confidence, reverse=True)[0]
