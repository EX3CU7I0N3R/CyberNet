import argparse
from datetime import datetime, timezone

import pandas as pd

from aggregation.flow_builder import build_flows, flows_to_dataframe
from aggregation.flow_metrics import compute_flow_metrics
from behavior.baselines import build_baseline_snapshot
from behavior.host_aggregator import build_host_profiles
from ingestion.parse import events_to_ndjson, extract_packet_info, parse_pcap


def main():
    parser = argparse.ArgumentParser(
        description="Behavioral Network Telemetry Analysis Platform"
    )
    parser.add_argument("pcap_file", help="Path to the PCAP file to analyze")
    parser.add_argument(
        "--ndjson-export",
        action="store_true",
        help="Deprecated: NDJSON export is enabled by default",
    )
    parser.add_argument(
        "--no-ndjson",
        action="store_true",
        help="Skip NDJSON export",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Skip CSV export",
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("BEHAVIORAL NETWORK TELEMETRY ANALYSIS")
    print("=" * 80 + "\n")

    print("[*] STEP 1: Parsing PCAP file...")
    try:
        packets = parse_pcap(args.pcap_file)
        print("    [OK] Capture opened\n")
    except Exception as exc:
        print(f"    [ERROR] {exc}\n")
        return

    print("[*] STEP 2: Normalizing packets to canonical events...")
    canonical_events = []
    failed_packets = 0

    for packet_index, packet in enumerate(packets):
        event = extract_packet_info(packet)
        if event is None:
            failed_packets += 1
            continue

        event.packet_index = packet_index
        event.replay_sequence_id = packet_index
        canonical_events.append(event)

    if not canonical_events:
        print("    [ERROR] No valid packets to analyze\n")
        return

    canonical_events = _assign_timeline_indexes(canonical_events)
    chronology_warnings = _packet_chronology_warnings(canonical_events)

    print(f"    [OK] Normalized {len(canonical_events):,} packets")
    if failed_packets:
        print(f"    [WARN] Failed to parse {failed_packets:,} packets")
    for warning in chronology_warnings:
        print(f"    [WARN] {warning}")
    print()

    print("[*] STEP 3: Building directional flows...")
    directional_flows = build_flows(canonical_events)
    flow_count = len(directional_flows)
    capture_duration = _capture_duration_seconds(canonical_events)
    total_bytes = sum(flow.initiator_bytes + flow.responder_bytes for flow in directional_flows.values())

    print(f"    [OK] Built {flow_count:,} directional flows")
    print(f"    [OK] Total traffic: {total_bytes:,} bytes")
    print(f"    [OK] Capture duration: {capture_duration:,.4f} seconds\n")

    print("[*] STEP 4: Computing behavioral metrics...")
    enriched_flows = compute_flow_metrics(canonical_events, directional_flows)
    scored_beacons = sum(1 for flow in enriched_flows if flow.beacon_score is not None)
    suppressed_flows = sum(1 for flow in enriched_flows if flow.suppressed)
    suspicious_flows = [flow for flow in enriched_flows if flow.is_suspicious]

    print(f"    [OK] Computed metrics for {flow_count:,} flows")
    print(f"    [OK] Suppressed expected infrastructure flows: {suppressed_flows:,}")
    print(f"    [OK] Beacon scoring eligible flows: {scored_beacons:,}")
    print(f"    [OK] Suspicious behavioral flow candidates: {len(suspicious_flows):,}\n")

    print("[*] STEP 5: Building host behavior profiles...")
    host_profiles = build_host_profiles(enriched_flows)
    elevated_hosts = [profile for profile in host_profiles if profile.risk_score >= 35]
    baseline_snapshot = build_baseline_snapshot(host_profiles)

    print(f"    [OK] Built {len(host_profiles):,} host profiles")
    print(f"    [OK] Hosts with elevated behavioral risk: {len(elevated_hosts):,}\n")

    print("[*] STEP 6: Analysis summary\n")
    _print_direction_summary(enriched_flows)
    _print_protocol_summary(enriched_flows)
    _print_suspicious_flows(suspicious_flows)
    _print_host_summary(elevated_hosts)

    print("[*] STEP 7: Exporting analysis artifacts...")
    if not args.no_csv:
        pd.DataFrame([event.model_dump() for event in canonical_events]).to_csv(
            "normalized_packets.csv",
            index=False,
        )
        flows_to_dataframe(directional_flows).to_csv("flows.csv", index=False)
        pd.DataFrame([flow.model_dump() for flow in enriched_flows]).to_csv(
            "enriched_flows.csv",
            index=False,
        )
        pd.DataFrame([profile.model_dump() for profile in host_profiles]).to_csv(
            "host_profiles.csv",
            index=False,
        )
        print("    [OK] Wrote CSV artifacts")

    if not args.no_ndjson:
        events_to_ndjson(canonical_events, "normalized_packets.ndjson")
        events_to_ndjson(list(directional_flows.values()), "flows.ndjson")
        events_to_ndjson(enriched_flows, "enriched_flows.ndjson")
        events_to_ndjson(host_profiles, "host_profiles.ndjson")
        events_to_ndjson([baseline_snapshot], "host_baseline_snapshot.ndjson")
        print("    [OK] Wrote NDJSON artifacts")

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80 + "\n")


def _assign_timeline_indexes(events):
    ordered_events = sorted(
        events,
        key=lambda event: (_parse_timestamp(event.timestamp), event.replay_sequence_id),
    )
    for timeline_index, event in enumerate(ordered_events):
        event.timeline_index = timeline_index
    return ordered_events


def _packet_chronology_warnings(events):
    warnings = []
    replay_sequence_ids = [event.replay_sequence_id for event in events]
    if replay_sequence_ids != sorted(replay_sequence_ids):
        warnings.append("Packet replay order differs from timestamp order; timeline_index preserves chronological replay.")
    return warnings


def _capture_duration_seconds(events) -> float:
    timestamps = [_parse_timestamp(event.timestamp) for event in events]
    if len(timestamps) < 2:
        return 0.0
    return round((max(timestamps) - min(timestamps)).total_seconds(), 4)


def _print_direction_summary(enriched_flows):
    directions = {}
    for flow in enriched_flows:
        directions[flow.direction] = directions.get(flow.direction, 0) + 1

    print("    Traffic Direction:")
    for direction, count in sorted(directions.items()):
        print(f"      - {direction:15s}: {count:>6,} flows")


def _print_protocol_summary(enriched_flows):
    protocols = {}
    for flow in enriched_flows:
        protocols[flow.application_protocol] = protocols.get(flow.application_protocol, 0) + 1

    print("\n    Protocol Classification:")
    for protocol, count in sorted(protocols.items(), key=lambda item: item[1], reverse=True)[:10]:
        print(f"      - {protocol:15s}: {count:>6,} flows")


def _print_suspicious_flows(suspicious_flows):
    print(f"\n    Behavioral Flow Candidates: {len(suspicious_flows):,}")
    for flow in sorted(suspicious_flows, key=lambda item: item.behavioral_score, reverse=True)[:5]:
        endpoint = f"{flow.initiator_ip}:{flow.initiator_port} -> {flow.responder_ip}:{flow.responder_port}"
        print(f"      - {endpoint}")
        print(
            f"        Score: {flow.behavioral_score:.1f} | Confidence: {flow.confidence:.1%} | Severity: {flow.severity}"
        )
        print(f"        Indicators: {', '.join(flow.suspicious_indicators)}")


def _print_host_summary(elevated_hosts):
    print("\n" + "=" * 80)
    print("HOST BEHAVIORAL SUMMARY")
    print("=" * 80)
    print(f"\n    Elevated Host Profiles: {len(elevated_hosts):,}")
    for profile in sorted(elevated_hosts, key=lambda item: item.risk_score, reverse=True)[:5]:
        print(f"\n    Host: {profile.ip_address}")
        print(f"    Risk Score: {profile.risk_score:.1f}")
        print(f"    Confidence: {profile.confidence:.1%}")
        print("\n    Indicators:")
        if profile.behavioral_indicators:
            for indicator in profile.behavioral_indicators:
                print(f"      - {indicator}")
        else:
            print("      - no_elevated_behavioral_indicators")
        print("\n    Connections:")
        print(f"      - External: {profile.external_connections}")
        print(f"      - Internal: {profile.internal_connections}")
        print("\n    Protocols:")
        for protocol in profile.protocols:
            print(f"      - {protocol}")


def _parse_timestamp(timestamp: str) -> datetime:
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp.astimezone(timezone.utc)


if __name__ == "__main__":
    main()
