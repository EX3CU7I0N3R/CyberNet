import unittest

from behavior.schemas import GraphNode, GraphState
from layer5.schemas import AttackHypothesis, InvestigationCandidate
from layer6.assessment_engine import AssessmentEngine
from layer6.confidence_explainer import ConfidenceExplainer
from layer6.investigation_planner import InvestigationPlanner
from layer6.narrative_engine.narrative_builder import NarrativeBuilder
from layer6.reasoning_engine import InvestigationReasoningEngine


class TestLayer6Quality(unittest.TestCase):
    def test_reasoning_generation(self):
        reasoning = InvestigationReasoningEngine().generate(self._primary_hypothesis())

        self.assertIn("destination was observed exclusively", reasoning)
        self.assertIn("Communication intervals remained consistent", reasoning)
        self.assertNotIn("periodicity", reasoning)

    def test_confidence_explanation(self):
        explainer = ConfidenceExplainer()
        drivers = explainer.confidence_drivers(self._primary_hypothesis())
        explanation = explainer.explain(self._primary_hypothesis())

        self.assertIn("destination exclusivity", drivers["high"])
        self.assertIn("periodic timing behavior", drivers["medium"])
        self.assertIn("multiple independent behavioral indicators", explanation)

    def test_negative_findings(self):
        findings = AssessmentEngine().negative_findings([self._primary_hypothesis()])

        self.assertTrue(findings)
        self.assertIn("No Layer 5 reconnaissance hypothesis", findings[0])

    def test_assessment_generation(self):
        assessment = AssessmentEngine().assess([self._primary_hypothesis()])

        self.assertIn("consistent with command-and-control beaconing", assessment)
        self.assertIn("Additional endpoint investigation is recommended", assessment)
        self.assertNotIn("Host compromised", assessment)

    def test_investigation_plan_generation(self):
        plan = InvestigationPlanner().plan([self._primary_hypothesis()])

        self.assertEqual(plan[0], "Review endpoint telemetry for the host during the capture window")
        self.assertGreaterEqual(len(plan), 5)

    def test_quality_scoring(self):
        narrative = NarrativeBuilder().build(self._candidate(), graph_context=self._graph_context())

        self.assertGreaterEqual(narrative.narrative_quality_score, 90)
        self.assertIn("investigation_reasoning", narrative.model_dump())
        self.assertEqual(narrative.risk_context["environment_rank"], 1)

    def _primary_hypothesis(self):
        return AttackHypothesis(
            hypothesis_id="h1",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="TLS beaconing: 10.2.28.88 <-> 45.131.214.85",
            impacted_entities=["10.2.28.88", "45.131.214.85"],
            supporting_evidence=[
                "periodicity",
                "persistence",
                "external_relationship",
                "low_jitter",
                "low_volume",
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

    def _candidate(self):
        hypothesis = self._primary_hypothesis()
        return InvestigationCandidate(
            host="10.2.28.88",
            host_role="WORKSTATION",
            priority="MEDIUM",
            priority_score=73.1,
            confidence=92.0,
            risk=74.0,
            hypotheses=[hypothesis],
            findings=[hypothesis],
        )

    def _graph_context(self):
        return GraphState(
            snapshot_id="graph",
            timestamp="2026-05-31T00:00:00Z",
            node_count=2,
            nodes=[
                GraphNode(node_id="n1", ip_address="10.2.28.88", risk_score=74.0),
                GraphNode(node_id="n2", ip_address="45.131.214.85", risk_score=55.0),
            ],
        )


if __name__ == "__main__":
    unittest.main()
