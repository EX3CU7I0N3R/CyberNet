from __future__ import annotations


class ChapterClassifier:
    TITLES = {
        "INITIAL_ACTIVITY": "Initial Network Activity",
        "NETWORK_DISCOVERY": "Network Discovery",
        "RELATIONSHIP_FORMATION": "Relationship Formation",
        "EXTERNAL_COMMUNICATION": "External Communication",
        "PERSISTENT_COMMUNICATION": "Persistent Communications",
        "BEHAVIORAL_ESCALATION": "Behavioral Escalation",
        "BEACONING_DEVELOPMENT": "Beaconing Indicators",
        "INVESTIGATION_TRIGGER": "Investigation Trigger",
        "INVESTIGATION_PRIORITY": "Investigation Priority",
        "UNKNOWN": "Unclassified Activity",
    }

    IMPORTANCE = {
        "INITIAL_ACTIVITY": 30,
        "NETWORK_DISCOVERY": 45,
        "RELATIONSHIP_FORMATION": 60,
        "EXTERNAL_COMMUNICATION": 65,
        "PERSISTENT_COMMUNICATION": 75,
        "BEHAVIORAL_ESCALATION": 82,
        "BEACONING_DEVELOPMENT": 90,
        "INVESTIGATION_TRIGGER": 95,
        "INVESTIGATION_PRIORITY": 100,
        "UNKNOWN": 20,
    }

    EVENT_TYPES = {
        "host_role_assigned": "INITIAL_ACTIVITY",
        "community_assigned": "INITIAL_ACTIVITY",
        "dns_query": "NETWORK_DISCOVERY",
        "dns_response": "NETWORK_DISCOVERY",
        "connection_created": "RELATIONSHIP_FORMATION",
        "connection_closed": "RELATIONSHIP_FORMATION",
        "tls_established": "EXTERNAL_COMMUNICATION",
        "http_session": "EXTERNAL_COMMUNICATION",
        "relationship_created": "RELATIONSHIP_FORMATION",
        "relationship_persistent": "PERSISTENT_COMMUNICATION",
        "periodicity_detected": "BEACONING_DEVELOPMENT",
        "rare_destination_detected": "BEACONING_DEVELOPMENT",
        "beaconing_started": "BEACONING_DEVELOPMENT",
        "beaconing_confidence_increased": "BEACONING_DEVELOPMENT",
        "host_risk_increased": "BEHAVIORAL_ESCALATION",
        "hypothesis_created": "INVESTIGATION_TRIGGER",
        "hypothesis_promoted": "INVESTIGATION_TRIGGER",
        "candidate_created": "INVESTIGATION_PRIORITY",
        "candidate_priority_changed": "INVESTIGATION_PRIORITY",
        "narrative_generated": "INVESTIGATION_PRIORITY",
    }

    SEVERITY_RANK = {
        "INFO": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    def classify(self, event) -> str:
        if event.event_type == "hypothesis_created" and event.metadata.get("hypothesis_type") == "beaconing":
            return "BEACONING_DEVELOPMENT"
        return self.EVENT_TYPES.get(event.event_type, "UNKNOWN")

    def title(self, chapter_type: str) -> str:
        return self.TITLES.get(chapter_type, self.TITLES["UNKNOWN"])

    def importance(self, chapter_type: str, events: list) -> float:
        base = self.IMPORTANCE.get(chapter_type, 20)
        severity_bonus = max((self.SEVERITY_RANK.get(event.severity, 0) for event in events), default=0) * 2
        volume_bonus = min(len(events) / 25, 8)
        return round(min(base + severity_bonus + volume_bonus, 100), 1)

    def severity(self, events: list) -> str:
        if not events:
            return "INFO"
        return max(events, key=lambda event: self.SEVERITY_RANK.get(event.severity, 0)).severity
