from __future__ import annotations

import json
from typing import Iterable, List

from .hypotheses import (
    AttackHypothesis,
    evaluate_beaconing,
    evaluate_host_sweep,
    evaluate_port_scan,
    evaluate_persistent_tls,
)
from .registry import HypothesisRegistry
from .schemas import BehavioralDelta


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

        # === RETURN TOP-10 ===
        return sorted(hypotheses, key=lambda h: (-h.confidence, h.severity != "critical", h.severity != "high"))[:10]

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
