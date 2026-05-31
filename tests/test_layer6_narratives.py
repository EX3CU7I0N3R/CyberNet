import json
import tempfile
import unittest

from layer5.schemas import AttackHypothesis, InvestigationCandidate
from layer6 import NarrativeManager, export_narratives
from layer6.narrative_engine.evidence_summarizer import EvidenceSummarizer
from layer6.narrative_engine.narrative_builder import NarrativeBuilder
from layer6.narrative_engine.recommendation_engine import RecommendationEngine


class TestLayer6Narratives(unittest.TestCase):
    def test_narrative_generation(self):
        narrative = NarrativeManager().build_narratives([self._candidate()])[0]

        self.assertEqual(narrative.host, "10.2.28.88")
        self.assertIn("45.131.214.85", narrative.executive_summary)
        self.assertIn("rare external destination", narrative.behavioral_summary)

    def test_assessment_generation(self):
        narrative = NarrativeBuilder().build(self._candidate())

        self.assertIn("consistent with command-and-control beaconing", narrative.assessment)
        self.assertNotIn("Malware detected", narrative.assessment)

    def test_recommendation_generation(self):
        recommendations = RecommendationEngine().recommendations_for(self._candidate().hypotheses)

        self.assertIn("Review endpoint telemetry", recommendations)
        self.assertIn("Identify initiating process", recommendations)
        self.assertIn("Investigate destination", recommendations)

    def test_confidence_explanation_generation(self):
        explanation = EvidenceSummarizer().confidence_explanation(
            ["periodicity", "persistence", "rare_destination", "exclusive_destination"],
            [],
        )

        self.assertIn("periodic timing characteristics", explanation)
        self.assertIn("destination exclusivity", explanation)

    def test_export_generation(self):
        narrative = NarrativeManager().build_narratives([self._candidate()])[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = f"{tmpdir}/investigation_narratives.ndjson"
            export_narratives([narrative], output_path)
            with open(output_path, encoding="utf-8") as stream:
                documents = [json.loads(line) for line in stream]

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["host"], "10.2.28.88")

    def _candidate(self):
        hypothesis = AttackHypothesis(
            hypothesis_id="h1",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="TLS beaconing: 10.2.28.88 <-> 45.131.214.85",
            impacted_entities=["10.2.28.88", "45.131.214.85"],
            supporting_evidence=[
                "periodicity",
                "persistence",
                "external_relationship",
                "rare_destination",
                "exclusive_destination",
            ],
            contradictory_evidence=[],
            confidence_explanation="Confidence 92%.",
            confidence=92.0,
            finding_tier="PRIMARY",
            created_at="2026-05-31T00:00:00Z",
            metadata={"relationship_destination": "45.131.214.85"},
        )
        return InvestigationCandidate(
            host="10.2.28.88",
            host_role="WORKSTATION",
            priority="HIGH",
            priority_score=80.0,
            confidence=92.0,
            risk=74.0,
            hypotheses=[hypothesis],
            findings=[hypothesis],
        )


if __name__ == "__main__":
    unittest.main()
