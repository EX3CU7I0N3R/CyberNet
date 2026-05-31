from __future__ import annotations

from layer6.assessment_engine import AssessmentEngine
from layer6.confidence_explainer import ConfidenceExplainer
from layer6.investigation_planner import InvestigationPlanner
from layer6.models import InvestigationNarrative
from layer6.reasoning_engine import InvestigationReasoningEngine

from .evidence_summarizer import EvidenceSummarizer
from .recommendation_engine import RecommendationEngine


ASSESSMENT_BY_HYPOTHESIS = {
    "beaconing": "Observed behavior is consistent with command-and-control beaconing.",
    "persistent_tls": "Observed behavior indicates persistent encrypted communication.",
    "port_scan": "Observed behavior suggests reconnaissance activity.",
    "host_sweep": "Observed behavior suggests reconnaissance activity across multiple peers.",
}


class NarrativeBuilder:
    def __init__(
        self,
        evidence_summarizer: EvidenceSummarizer | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        reasoning_engine: InvestigationReasoningEngine | None = None,
        assessment_engine: AssessmentEngine | None = None,
        confidence_explainer: ConfidenceExplainer | None = None,
        investigation_planner: InvestigationPlanner | None = None,
    ):
        self.evidence_summarizer = evidence_summarizer or EvidenceSummarizer()
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.reasoning_engine = reasoning_engine or InvestigationReasoningEngine()
        self.assessment_engine = assessment_engine or AssessmentEngine()
        self.confidence_explainer = confidence_explainer or ConfidenceExplainer()
        self.investigation_planner = investigation_planner or InvestigationPlanner()

    def build(self, candidate, host_profile=None, graph_context=None) -> InvestigationNarrative:
        hypotheses = list(candidate.hypotheses or candidate.findings)
        primary_hypothesis = self._primary_hypothesis(hypotheses)
        supporting_evidence = primary_hypothesis.supporting_evidence if primary_hypothesis else []
        contradictory_evidence = primary_hypothesis.contradictory_evidence if primary_hypothesis else []
        risk_context = self._risk_context(candidate, graph_context)
        confidence_drivers = self.confidence_explainer.confidence_drivers(primary_hypothesis)
        investigation_reasoning = self.reasoning_engine.generate(primary_hypothesis)
        assessment = self.assessment_engine.assess(hypotheses)
        negative_findings = self.assessment_engine.negative_findings(hypotheses)
        investigation_plan = self.investigation_planner.plan(hypotheses)

        narrative = InvestigationNarrative(
            host=candidate.host,
            priority=candidate.priority,
            confidence=candidate.confidence,
            risk_context=risk_context,
            executive_summary=self._executive_summary(candidate, primary_hypothesis),
            behavioral_summary=self.evidence_summarizer.behavioral_summary(supporting_evidence),
            evidence_summary=self.evidence_summarizer.evidence_summary(supporting_evidence, contradictory_evidence),
            investigation_reasoning=investigation_reasoning,
            confidence_drivers=confidence_drivers,
            negative_findings=negative_findings,
            assessment=assessment,
            confidence_explanation=self.confidence_explainer.explain(primary_hypothesis),
            recommended_actions=self.recommendation_engine.recommendations_for(hypotheses),
            investigation_plan=investigation_plan,
            supporting_hypotheses=[hypothesis.hypothesis_id for hypothesis in hypotheses],
        )
        narrative.narrative_quality_score = self._quality_score(narrative)
        return narrative

    def _executive_summary(self, candidate, primary_hypothesis) -> str:
        destination = ""
        if primary_hypothesis:
            destination = primary_hypothesis.metadata.get("relationship_destination", "")
        destination_clause = f" with external destination {destination}" if destination else " with an external destination"
        return (
            f"Host {candidate.host} established persistent low-volume communication{destination_clause}. "
            "The behavior is unusual compared to other observed relationships and was prioritized for analyst investigation."
        )

    def _assessment(self, hypotheses: list) -> str:
        assessments = []
        for hypothesis in hypotheses:
            assessment = ASSESSMENT_BY_HYPOTHESIS.get(
                hypothesis.hypothesis_type,
                "Observed activity suggests behavior that warrants analyst review.",
            )
            if assessment not in assessments:
                assessments.append(assessment)
        return " ".join(assessments)

    def _risk_context(self, candidate, graph_context) -> dict:
        environment_rank = None
        host_count = None
        if graph_context is not None:
            host_count = getattr(graph_context, "node_count", None)
            ranked_nodes = sorted(
                getattr(graph_context, "nodes", []),
                key=lambda node: getattr(node, "risk_score", 0.0),
                reverse=True,
            )
            for index, node in enumerate(ranked_nodes, 1):
                if getattr(node, "ip_address", None) == candidate.host:
                    environment_rank = index
                    break

        return {
            "host_risk": candidate.risk,
            "priority": candidate.priority,
            "environment_rank": environment_rank,
            "environment_size": host_count,
            "selection_reason": "This host was selected because it represents the highest-priority investigation candidate identified during analysis.",
        }

    def _quality_score(self, narrative: InvestigationNarrative) -> float:
        checks = [
            bool(narrative.executive_summary),
            bool(narrative.investigation_reasoning),
            bool(narrative.assessment),
            bool(narrative.confidence_explanation),
            bool(narrative.investigation_plan),
            bool(narrative.negative_findings),
        ]
        return round(sum(1 for passed in checks if passed) / len(checks) * 100, 1)

    def _primary_hypothesis(self, hypotheses: list):
        if not hypotheses:
            return None
        primary = [hypothesis for hypothesis in hypotheses if hypothesis.finding_tier == "PRIMARY"]
        if primary:
            return sorted(primary, key=lambda hypothesis: hypothesis.confidence, reverse=True)[0]
        return sorted(hypotheses, key=lambda hypothesis: hypothesis.confidence, reverse=True)[0]
