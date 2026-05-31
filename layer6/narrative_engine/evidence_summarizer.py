from __future__ import annotations

from typing import Iterable


EVIDENCE_PHRASES = {
    "periodicity": "recurring communication timing",
    "persistence": "a relationship that persisted across the capture window",
    "external_relationship": "communication with an external destination",
    "rare_destination": "a rare external destination",
    "exclusive_destination": "a destination used only by this host",
    "low_volume": "low-volume traffic characteristics",
    "low_jitter": "stable timing between communications",
    "common_cloud_service": "the destination resembles common cloud service infrastructure",
    "shared_destination": "the destination is shared by multiple internal hosts",
    "many_internal_consumers": "many internal hosts use the same destination",
    "high_destination_fan_in": "the destination has high internal fan-in",
    "infrastructure_role": "the destination has an infrastructure-like role",
}


class EvidenceSummarizer:
    def behavioral_summary(self, evidence_items: Iterable[str]) -> str:
        phrases = self._phrases(evidence_items)
        if not phrases:
            return "Observed behavior was prioritized based on the correlated investigation findings."
        return "The host demonstrated " + self._join_phrases(phrases) + "."

    def evidence_summary(self, supporting_evidence: Iterable[str], contradictory_evidence: Iterable[str]) -> str:
        supporting = self._phrases(supporting_evidence)
        contradictory = self._phrases(contradictory_evidence)
        if not contradictory:
            return "Supporting evidence includes " + self._join_phrases(supporting) + ". No contradictory evidence was observed for the primary finding."
        return (
            "Supporting evidence includes "
            + self._join_phrases(supporting)
            + ". Contradictory context includes "
            + self._join_phrases(contradictory)
            + "."
        )

    def confidence_explanation(self, supporting_evidence: Iterable[str], contradictory_evidence: Iterable[str]) -> str:
        supporting = set(supporting_evidence)
        reasons = []
        if "periodicity" in supporting:
            reasons.append("periodic timing characteristics")
        if "persistence" in supporting:
            reasons.append("relationship persistence")
        if "rare_destination" in supporting:
            reasons.append("destination rarity")
        if "exclusive_destination" in supporting:
            reasons.append("destination exclusivity")
        if not reasons:
            reasons.append("multiple correlated behavioral indicators")

        explanation = "Confidence is elevated because the communication demonstrates " + self._join_phrases(reasons) + "."
        contradictory = self._phrases(contradictory_evidence)
        if contradictory:
            explanation += " Confidence is tempered by " + self._join_phrases(contradictory) + "."
        return explanation

    def _phrases(self, evidence_items: Iterable[str]) -> list[str]:
        phrases = []
        for evidence_item in evidence_items:
            phrase = EVIDENCE_PHRASES.get(str(evidence_item), str(evidence_item).replace("_", " "))
            if phrase not in phrases:
                phrases.append(phrase)
        return phrases

    def _join_phrases(self, phrases: list[str]) -> str:
        if not phrases:
            return "no notable evidence"
        if len(phrases) == 1:
            return phrases[0]
        if len(phrases) == 2:
            return f"{phrases[0]} and {phrases[1]}"
        return ", ".join(phrases[:-1]) + f", and {phrases[-1]}"
