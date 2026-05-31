from __future__ import annotations


REASONING_BY_EVIDENCE = {
    "exclusive_destination": "The destination was observed exclusively for this host.",
    "rare_destination": "The destination was rare within the observed environment.",
    "periodicity": "Communication intervals remained consistent throughout the capture.",
    "low_jitter": "The timing pattern had limited variation between communications.",
    "persistence": "The relationship persisted across multiple observation windows.",
    "low_volume": "Traffic volume stayed low, which can make recurring communication less obvious in aggregate flow views.",
    "external_relationship": "The relationship crossed the internal network boundary to an external destination.",
}


class InvestigationReasoningEngine:
    def generate(self, hypothesis) -> str:
        if not hypothesis:
            return "The available investigation context did not include a primary hypothesis to reason from."

        statements = []
        for evidence_item in hypothesis.supporting_evidence:
            statement = REASONING_BY_EVIDENCE.get(evidence_item)
            if statement and statement not in statements:
                statements.append(statement)

        if hypothesis.hypothesis_type == "beaconing":
            statements.append("Together, these characteristics are commonly associated with beaconing behavior.")

        if not statements:
            statements.append("The finding was prioritized because multiple behavioral indicators point to the same investigation path.")

        return " ".join(statements)
