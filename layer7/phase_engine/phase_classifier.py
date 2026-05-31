from __future__ import annotations


class PhaseClassifier:
    PHASE_BY_EVENT = {
        "dns_query": "Discovery",
        "dns_response": "Discovery",
        "connection_created": "Communication",
        "connection_closed": "Communication",
        "tls_established": "Communication",
        "http_session": "Communication",
        "relationship_created": "Communication",
        "relationship_persistent": "Persistence",
        "periodicity_detected": "Beaconing",
        "rare_destination_detected": "Beaconing",
        "beaconing_started": "Beaconing",
        "beaconing_confidence_increased": "Beaconing",
        "host_risk_increased": "Investigation",
        "host_role_assigned": "Investigation",
        "community_assigned": "Investigation",
        "community_changed": "Investigation",
        "hypothesis_created": "Investigation",
        "hypothesis_promoted": "Investigation",
        "candidate_created": "Investigation",
        "candidate_priority_changed": "Investigation",
        "narrative_generated": "Investigation",
    }

    def classify(self, event) -> str:
        return self.PHASE_BY_EVENT.get(event.event_type, "Unknown")
