from datetime import datetime, timezone
from hashlib import sha256
from typing import Dict, Iterable, List

from behavior.schemas import HostBaselineSnapshot, HostProfile


BASELINE_FIELDS = (
    "flow_count",
    "packet_count",
    "total_bytes",
    "upload_bytes",
    "download_bytes",
    "external_connections",
    "internal_connections",
    "unique_destinations",
    "unique_ports",
    "protocol_diversity",
    "beacon_flow_count",
    "suspicious_flow_count",
    "persistent_connection_count",
    "long_lived_flow_count",
    "active_duration",
    "activity_density",
    "risk_score",
    "confidence",
)


def build_baseline_snapshot(host_profiles: Iterable[HostProfile], snapshot_id: str | None = None) -> HostBaselineSnapshot:
    profiles = list(host_profiles)
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    normalized_hosts = {profile.ip_address: normalize_host_state(profile) for profile in profiles}
    stable_id = snapshot_id or _snapshot_id(generated_at, normalized_hosts)

    return HostBaselineSnapshot(
        snapshot_id=stable_id,
        generated_at=generated_at,
        host_count=len(profiles),
        hosts=normalized_hosts,
    )


def normalize_host_state(profile: HostProfile) -> Dict:
    state = {field: getattr(profile, field) for field in BASELINE_FIELDS}
    state.update({
        "ip_address": profile.ip_address,
        "protocols": profile.protocols,
        "transports": profile.transports,
        "first_seen": profile.first_seen,
        "last_seen": profile.last_seen,
        "first_seen_sequence": profile.first_seen_sequence,
        "last_seen_sequence": profile.last_seen_sequence,
        "active_time_buckets": profile.active_time_buckets,
        "hourly_activity_distribution": profile.hourly_activity_distribution,
        "behavioral_indicators": profile.behavioral_indicators,
    })
    return state


def diff_host_states(previous: Dict, current: Dict) -> Dict:
    numeric_changes = {}
    for field in BASELINE_FIELDS:
        before = previous.get(field, 0)
        after = current.get(field, 0)
        if before != after:
            numeric_changes[field] = {
                "previous": before,
                "current": after,
                "delta": round(after - before, 4),
            }

    return {
        "host": current.get("ip_address") or previous.get("ip_address"),
        "numeric_changes": numeric_changes,
        "new_indicators": sorted(set(current.get("behavioral_indicators", [])) - set(previous.get("behavioral_indicators", []))),
        "removed_indicators": sorted(set(previous.get("behavioral_indicators", [])) - set(current.get("behavioral_indicators", []))),
    }


def _snapshot_id(generated_at: str, hosts: Dict[str, Dict]) -> str:
    digest_input = generated_at + "|" + "|".join(sorted(hosts))
    return sha256(digest_input.encode()).hexdigest()[:16]
