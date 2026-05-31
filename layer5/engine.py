from __future__ import annotations

import json
from typing import Iterable, List

from .hypotheses import (
    AttackHypothesis,
    deduplicate_evidence,
    evaluate_beaconing,
    evaluate_host_sweep,
    evaluate_port_scan,
    evaluate_persistent_tls,
)
from .registry import HypothesisRegistry
from .schemas import BehavioralDelta, HostInvestigationSummary, InvestigationCandidate
from behavior.role_manager import (
    DOMAIN_CONTROLLER,
    EXTERNAL_SERVICE,
    INFRASTRUCTURE,
    SERVER,
    UNKNOWN,
    WORKSTATION,
    normalize_role,
    role_to_display,
)


def _export_to_ndjson(objects: Iterable, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as stream:
        for obj in objects:
            document = obj.dict() if hasattr(obj, "dict") else obj
            stream.write(json.dumps(document) + "\n")


class Layer5Phase1Engine:
    def __init__(self, registry: HypothesisRegistry | None = None):
        self.registry = registry or HypothesisRegistry()

    def evaluate(
        self,
        host_deltas: Iterable[BehavioralDelta],
        relationship_deltas: Iterable[BehavioralDelta],
        host_profiles_by_ip: dict | None = None,
    ) -> List[AttackHypothesis]:
        """
        Evaluate hypotheses with full hardening:
        - Filter <60% confidence
        - Deduplicate host-centric (merge reverse relationships)
        - Keep top-3 per host, top-1 per relationship
        - Return top-10 overall
        """
        host_deltas = list(host_deltas)
        relationship_deltas = list(relationship_deltas)
        host_profiles_by_ip = host_profiles_by_ip or {}
        hypotheses: List[AttackHypothesis] = []

        hypotheses.extend(evaluate_port_scan(self.registry, host_deltas, host_profiles_by_ip))
        hypotheses.extend(evaluate_host_sweep(self.registry, host_deltas, host_profiles_by_ip))
        hypotheses.extend(evaluate_beaconing(self.registry, relationship_deltas, host_profiles_by_ip))
        hypotheses.extend(evaluate_persistent_tls(self.registry, relationship_deltas, host_profiles_by_ip))

        # === FILTER <60% CONFIDENCE ===
        hypotheses = [h for h in hypotheses if h.confidence >= 60.0]

        # === DEDUPLICATE HOST-CENTRIC (merge reverse relationships) ===
        hypotheses = self._deduplicate_host_centric(hypotheses)

        # === TOP-N LIMITER: Keep top-3 per host, top-1 per relationship ===
        hypotheses = self._apply_top_n_limits(hypotheses)

        for hypothesis in hypotheses:
            hypothesis.asset_criticality_score = self._asset_criticality_for_hypothesis(hypothesis, host_profiles_by_ip)
            hypothesis.priority_score = self.compute_hypothesis_priority(hypothesis, host_profiles_by_ip)
            hypothesis.priority_level = self._priority_level(hypothesis.priority_score)

        return sorted(hypotheses, key=lambda h: (-h.priority_score, -h.confidence))[:10]

    def compute_hypothesis_priority(self, hypothesis: AttackHypothesis, host_profiles_by_ip: dict | None = None) -> float:
        host_profiles_by_ip = host_profiles_by_ip or {}
        host_risk = self._host_risk_for_hypothesis(hypothesis, host_profiles_by_ip)
        asset_criticality = self._asset_criticality_for_hypothesis(hypothesis, host_profiles_by_ip)
        return compute_priority_score(host_risk, hypothesis.confidence, asset_criticality)

    def build_host_investigation_summaries(
        self,
        hypotheses: Iterable[AttackHypothesis],
        host_profiles_by_ip: dict | None = None,
    ) -> List[HostInvestigationSummary]:
        host_profiles_by_ip = host_profiles_by_ip or {}
        summaries: dict[str, HostInvestigationSummary] = {}

        for hypothesis in hypotheses:
            investigation_host = self._investigation_host(hypothesis, host_profiles_by_ip)
            if investigation_host not in summaries:
                profile = host_profiles_by_ip.get(investigation_host)
                host_summary = self._host_summary(investigation_host, profile)
                summaries[investigation_host] = HostInvestigationSummary(
                    host=investigation_host,
                    host_risk=host_summary["risk_score"],
                    asset_criticality_score=self._asset_criticality_for_role(host_summary["host_role"], investigation_host),
                    host_summary=host_summary,
                )

            summary = summaries[investigation_host]
            summary.findings.append(hypothesis)
            summary.hypothesis_count += 1
            summary.highest_confidence = max(summary.highest_confidence, hypothesis.confidence)
            summary.priority_score = max(summary.priority_score, hypothesis.priority_score)

        return sorted(summaries.values(), key=lambda item: (-item.priority_score, -item.highest_confidence))

    def build_investigation_candidates(
        self,
        hypotheses: Iterable[AttackHypothesis],
        host_profiles_by_ip: dict | None = None,
    ) -> List[InvestigationCandidate]:
        summaries = self.build_host_investigation_summaries(hypotheses, host_profiles_by_ip)
        candidates: List[InvestigationCandidate] = []

        for summary in summaries[:3]:
            top_finding = summary.findings[0] if summary.findings else None
            supporting_evidence = deduplicate_evidence(top_finding.supporting_evidence if top_finding else [])
            candidate_rationale = self._candidate_rationale(summary, supporting_evidence)

            candidates.append(InvestigationCandidate(
                host=summary.host,
                host_role=normalize_role(summary.host_summary.get("host_role")),
                priority=self._priority_level(summary.priority_score),
                priority_score=summary.priority_score,
                priority_explanation=self._priority_explanation(summary),
                confidence=summary.highest_confidence,
                risk=summary.host_risk,
                asset_criticality_score=summary.asset_criticality_score,
                candidate_rationale=candidate_rationale,
                host_summary=summary.host_summary,
                rationale=supporting_evidence,
                recommended_actions=[
                    "inspect endpoint",
                    "review EDR telemetry",
                    "check destination reputation",
                    "examine process activity",
                ],
                narrative_context={
                    "host": summary.host,
                    "findings": [finding.model_dump() for finding in summary.findings],
                    "recommended_actions": [
                        "inspect endpoint",
                        "review EDR telemetry",
                        "check destination reputation",
                        "examine process activity",
                    ],
                },
                hypotheses=summary.findings,
                findings=summary.findings,
            ))

        return candidates

    def _priority_explanation(self, summary: HostInvestigationSummary) -> dict:
        return {
            "priority_score": summary.priority_score,
            "computed_from": {
                "host_risk": {
                    "value": summary.host_risk,
                    "weight": 0.35,
                    "contribution": round(summary.host_risk * 0.35, 2),
                },
                "confidence": {
                    "value": summary.highest_confidence,
                    "weight": 0.35,
                    "contribution": round(summary.highest_confidence * 0.35, 2),
                },
                "asset_criticality": {
                    "value": summary.asset_criticality_score,
                    "weight": 0.30,
                    "contribution": round(summary.asset_criticality_score * 0.30, 2),
                },
            },
        }

    def _host_risk_for_hypothesis(self, hypothesis: AttackHypothesis, host_profiles_by_ip: dict) -> float:
        investigation_host = self._investigation_host(hypothesis, host_profiles_by_ip)
        return float(getattr(host_profiles_by_ip.get(investigation_host), "risk_score", 0.0))

    def _asset_criticality_for_hypothesis(self, hypothesis: AttackHypothesis, host_profiles_by_ip: dict) -> float:
        investigation_host = self._investigation_host(hypothesis, host_profiles_by_ip)
        profile = host_profiles_by_ip.get(investigation_host)
        role = self._display_host_role(investigation_host, profile)
        return self._asset_criticality_for_role(role, investigation_host)

    def _asset_criticality_for_role(self, host_role: str, host: str) -> float:
        normalized_role = host_role.lower().replace(" ", "_")
        role_scores = {
            DOMAIN_CONTROLLER: 100.0,
            INFRASTRUCTURE: 80.0,
            SERVER: 70.0,
            WORKSTATION: 50.0,
            EXTERNAL_SERVICE: 20.0,
            UNKNOWN: 40.0,
        }
        if self._is_external_host(host):
            return role_scores[EXTERNAL_SERVICE]
        return role_scores.get(normalize_role(normalized_role), role_scores[UNKNOWN])

    def _host_summary(self, host: str, profile) -> dict:
        return {
            "risk_score": float(getattr(profile, "risk_score", 0.0)),
            "host_role": self._display_host_role(host, profile),
            "role_confidence": float(getattr(profile, "role_confidence", 0.0)),
            "external_relationships": int(getattr(profile, "external_unique_hosts", 0)),
            "internal_relationships": int(getattr(profile, "internal_unique_hosts", 0)),
            "top_protocols": list(getattr(profile, "protocols", []))[:5],
        }

    def _display_host_role(self, host: str, profile) -> str:
        role = getattr(profile, "role", getattr(profile, "inferred_role", UNKNOWN))
        return role_to_display(role)

    def _candidate_rationale(self, summary: HostInvestigationSummary, supporting_evidence: List[str]) -> str:
        destination = ""
        top_finding = summary.findings[0] if summary.findings else None
        if top_finding:
            destination = top_finding.metadata.get("relationship_destination", "")
        if "rare_destination" in supporting_evidence and "exclusive_destination" in supporting_evidence:
            return (
                f"Host exhibits persistent low-volume communication with rare and exclusive external destination {destination}."
            ).strip()
        if "persistence" in supporting_evidence and "periodicity" in supporting_evidence:
            return "Host exhibits persistent communication with periodic timing behavior."
        return "Host has prioritized findings based on risk, confidence, and asset criticality."

    def _is_external_host(self, host: str) -> bool:
        import ipaddress

        try:
            return not ipaddress.ip_address(host).is_private
        except ValueError:
            return False

    def _investigation_host(self, hypothesis: AttackHypothesis, host_profiles_by_ip: dict) -> str:
        consumer = hypothesis.metadata.get("relationship_consumer")
        if consumer:
            return consumer
        known_hosts = [host for host in hypothesis.impacted_entities if host in host_profiles_by_ip]
        if known_hosts:
            return max(known_hosts, key=lambda host: float(getattr(host_profiles_by_ip[host], "risk_score", 0.0)))
        return hypothesis.impacted_entities[0] if hypothesis.impacted_entities else "unknown"

    def _priority_level(self, priority_score: float) -> str:
        if priority_score >= 90.0:
            return "CRITICAL"
        if priority_score >= 75.0:
            return "HIGH"
        if priority_score >= 60.0:
            return "MEDIUM"
        if priority_score >= 40.0:
            return "LOW"
        return "INFORMATIONAL"

    def _deduplicate_host_centric(self, hypotheses: List[AttackHypothesis]) -> List[AttackHypothesis]:
        """
        Merge X->Y and Y->X into single hypothesis.
        Prefer: initiator -> responder.
        """
        if not hypotheses:
            return []

        seen_pairs: dict = {}
        result: List[AttackHypothesis] = []

        for h in hypotheses:
            if h.hypothesis_type != "beaconing":
                result.append(h)
                continue

            # For beaconing, deduplicate on (source, target) unordered pair
            if len(h.impacted_entities) == 2:
                source, target = h.impacted_entities[0], h.impacted_entities[1]
                pair_key = tuple(sorted([source, target]))

                if pair_key in seen_pairs:
                    # Keep the existing one (first occurrence wins)
                    continue
                seen_pairs[pair_key] = True
            result.append(h)

        return result

    def _apply_top_n_limits(self, hypotheses: List[AttackHypothesis]) -> List[AttackHypothesis]:
        """
        Keep top-3 per host, top-1 per relationship.
        """
        from collections import defaultdict

        host_hypotheses: dict = defaultdict(list)
        relationship_hypotheses: dict = defaultdict(list)

        for h in hypotheses:
            if h.hypothesis_type == "beaconing" and len(h.impacted_entities) == 2:
                # Track by unordered pair
                rel_key = tuple(sorted(h.impacted_entities))
                relationship_hypotheses[rel_key].append(h)
            else:
                # Track per host
                for host_id in h.impacted_entities:
                    host_hypotheses[host_id].append(h)

        result: List[AttackHypothesis] = []

        # Keep top-1 per relationship
        for rel_key, h_list in relationship_hypotheses.items():
            sorted_h = sorted(h_list, key=lambda h: (-h.confidence, h.severity != "critical"))
            result.append(sorted_h[0])

        # Keep top-3 per host (for non-beaconing)
        for host_id, h_list in host_hypotheses.items():
            sorted_h = sorted(h_list, key=lambda h: (-h.confidence, h.severity != "critical"))
            result.extend(sorted_h[:3])

        return result

    def export_hypotheses(self, hypotheses: Iterable[AttackHypothesis], output_path: str) -> None:
        _export_to_ndjson(hypotheses, output_path)

    def export_deltas(self, deltas: Iterable[BehavioralDelta], output_path: str) -> None:
        _export_to_ndjson(deltas, output_path)


def compute_priority_score(host_risk: float, hypothesis_confidence: float, asset_criticality: float) -> float:
    return round(
        host_risk * 0.35
        + hypothesis_confidence * 0.35
        + asset_criticality * 0.30,
        2,
    )
