from __future__ import annotations


class EventClassifier:
    def flow_event_type(self, flow) -> str:
        protocol = getattr(flow, "application_protocol", "")
        if protocol == "dns":
            return "dns_query"
        if protocol == "http":
            return "http_session"
        if protocol == "https" or getattr(flow, "responder_port", None) == 443:
            return "tls_established"
        return "connection_created"

    def severity_for_score(self, score: float, default: str = "INFO") -> str:
        if score >= 90:
            return "CRITICAL"
        if score >= 70:
            return "HIGH"
        if score >= 40:
            return "MEDIUM"
        if score > 0:
            return "LOW"
        return default

    def severity_for_label(self, label: str) -> str:
        normalized = str(label or "").upper()
        if normalized in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}:
            return normalized
        if normalized == "INFORMATIONAL":
            return "INFO"
        return "INFO"
