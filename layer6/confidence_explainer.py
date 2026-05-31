from __future__ import annotations


DRIVER_LABELS = {
    "exclusive_destination": "destination exclusivity",
    "rare_destination": "destination rarity",
    "periodicity": "periodic timing behavior",
    "low_jitter": "stable timing behavior",
    "persistence": "relationship persistence",
    "low_volume": "low-volume communication",
    "external_relationship": "external communication path",
}


class ConfidenceExplainer:
    def confidence_drivers(self, hypothesis) -> dict[str, list[str]]:
        evidence = set(hypothesis.supporting_evidence if hypothesis else [])
        drivers = {"high": [], "medium": [], "low": []}

        for evidence_item in ("exclusive_destination", "rare_destination"):
            if evidence_item in evidence:
                drivers["high"].append(DRIVER_LABELS[evidence_item])

        for evidence_item in ("periodicity", "low_jitter", "persistence"):
            if evidence_item in evidence:
                drivers["medium"].append(DRIVER_LABELS[evidence_item])

        for evidence_item in ("low_volume", "external_relationship"):
            if evidence_item in evidence:
                drivers["low"].append(DRIVER_LABELS[evidence_item])

        return drivers

    def explain(self, hypothesis) -> str:
        drivers = self.confidence_drivers(hypothesis)
        populated = [driver for values in drivers.values() for driver in values]
        if not populated:
            return "Confidence is based on multiple correlated behavioral indicators supporting the same hypothesis."

        explanation = (
            "Overall confidence is elevated because multiple independent behavioral indicators support the same hypothesis."
        )
        if drivers["high"]:
            explanation += " The strongest drivers are " + self._join(drivers["high"]) + "."
        if drivers["medium"]:
            explanation += " Additional support comes from " + self._join(drivers["medium"]) + "."
        if drivers["low"]:
            explanation += " Lower-impact context includes " + self._join(drivers["low"]) + "."
        return explanation

    def _join(self, values: list[str]) -> str:
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return ", ".join(values[:-1]) + f", and {values[-1]}"
