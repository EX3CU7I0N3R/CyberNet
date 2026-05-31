from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List


class EventCorrelator:
    def correlate(self, events: Iterable) -> List:
        deduplicated = {}
        for event in events:
            key = (
                event.event_type,
                event.host,
                tuple(sorted(event.related_hosts)),
                event.metadata.get("flow_id") or event.metadata.get("edge_id") or event.metadata.get("hypothesis_id") or "",
            )
            current = deduplicated.get(key)
            if current is None or self._order_key(event) < self._order_key(current):
                deduplicated[key] = event
        return sorted(deduplicated.values(), key=self._order_key)

    def _order_key(self, event):
        try:
            timestamp = datetime.fromisoformat(str(event.timestamp).replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        except Exception:
            timestamp = datetime.min.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc), event.event_id
