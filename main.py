import argparse
from datetime import datetime, timezone

import pandas as pd

from aggregation.flow_builder import build_flows, flows_to_dataframe
from aggregation.flow_metrics import compute_flow_metrics
from behavior.baselines import build_baseline_snapshot
from behavior.graph_builder import build_graph_edges, build_graph_nodes, compute_graph_hashes
from behavior.graph_metrics import compute_graph_metrics
from behavior.graph_state import build_graph_state, build_temporal_snapshots
from behavior.host_aggregator import build_host_profiles
from behavior.relationships import build_relationships
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
    relationships = build_relationships(enriched_flows)
    elevated_hosts = [profile for profile in host_profiles if profile.risk_score >= 35]
    baseline_snapshot = build_baseline_snapshot(host_profiles)

    print(f"    [OK] Built {len(host_profiles):,} host profiles")
    print(f"    [OK] Built {len(relationships):,} host relationships")
    print(f"    [OK] Hosts with elevated behavioral risk: {len(elevated_hosts):,}\n")

    print("[*] STEP 6: Building graph state...")
    graph_state = build_graph_state(host_profiles, relationships)
    print(f"    [OK] Built graph with {graph_state.node_count:,} nodes and {graph_state.edge_count:,} edges")
    print(f"    [OK] Graph density: {graph_state.graph_density:.6f}")
    print(f"    [OK] Graph risk score: {graph_state.graph_risk_score:.1f}\n")

    print("[*] STEP 7: Generating temporal snapshots...")
    temporal_snapshots = build_temporal_snapshots(host_profiles, relationships, snapshot_interval_seconds=60)
    print(f"    [OK] Generated {len(temporal_snapshots):,} temporal snapshots")
    if temporal_snapshots:
        print(f"    [OK] Snapshot time window: {temporal_snapshots[0].window_start} to {temporal_snapshots[-1].window_end}\n")
    else:
        print()

    print("[*] STEP 8: Analysis summary\n")
    _print_direction_summary(enriched_flows)
    _print_protocol_summary(enriched_flows)
    _print_suspicious_flows(suspicious_flows)
    _print_host_summary(elevated_hosts)
    _print_graph_summary(graph_state, temporal_snapshots)

    print("[*] STEP 9: Exporting analysis artifacts...")
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
        pd.DataFrame([relationship.model_dump() for relationship in relationships]).to_csv(
            "relationships.csv",
            index=False,
        )
        print("    [OK] Wrote CSV artifacts")

    if not args.no_ndjson:
        events_to_ndjson(canonical_events, "normalized_packets.ndjson")
        events_to_ndjson(list(directional_flows.values()), "flows.ndjson")
        events_to_ndjson(enriched_flows, "enriched_flows.ndjson")
        events_to_ndjson(host_profiles, "host_profiles.ndjson")
        events_to_ndjson(relationships, "relationships.ndjson")
        events_to_ndjson([baseline_snapshot], "host_baseline_snapshot.ndjson")
        events_to_ndjson(graph_state.nodes, "graph_nodes.ndjson")
        events_to_ndjson(graph_state.edges, "graph_edges.ndjson")
        events_to_ndjson(temporal_snapshots, "graph_snapshots.ndjson")
        events_to_ndjson([graph_state], "graph_state.ndjson")
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
        print(f"    Inferred Role: {profile.inferred_role} ({profile.role_confidence:.1%})")
        print(f"    Risk Score: {profile.risk_score:.1f}")
        print(f"    Confidence: {profile.confidence:.1%}")
        print("\n    Indicators:")
        if profile.behavioral_indicators:
            for indicator in profile.behavioral_indicators:
                print(f"      - {indicator}")
        else:
            print("      - no_elevated_behavioral_indicators")
        print("\n    Connections:")
        print(f"      - External unique hosts: {profile.external_unique_hosts}")
        print(f"      - External flows: {profile.external_flow_count}")
        print(f"      - Internal unique hosts: {profile.internal_unique_hosts}")
        print(f"      - Internal flows: {profile.internal_flow_count}")
        print("\n    Protocols:")
        for protocol in profile.protocols:
            print(f"      - {protocol}")


def _print_graph_summary(graph_state, temporal_snapshots):
    """FINAL HARDENED: Graph summary with all Layer 4 intelligence fixes."""
    print("\n" + "=" * 80)
    print("GRAPH STATE SUMMARY (LAYER 4 HARDENED - FINAL)")
    print("=" * 80)
    
    # === FIX 1+2: Basic Topology with Noise Suppression ===
    print(f"\n    Graph Topology:")
    print(f"      Nodes: {graph_state.node_count}")
    print(f"      Edges: {graph_state.edge_count}")
    print(f"      Density: {graph_state.graph_density:.6f}")
    print(f"      Isolated: {graph_state.isolated_node_count}")
    
    # === FIX 2: Behavioral Communities (with percentages) ===
    communities = graph_state.metadata.get("communities", {})
    if communities:
        print(f"\n    Behavioral Communities:")
        total_nodes = sum(len(ips) for ips in communities.values())
        for community_name in sorted(communities.keys()):
            ips = communities[community_name]
            percentage = (len(ips) / total_nodes * 100) if total_nodes > 0 else 0
            print(f"      {community_name}: {len(ips)} ({percentage:.1f}%)")
    
    # === FIX 3: Explainable Graph Risk Breakdown ===
    print(f"\n    Graph Risk Score: {graph_state.graph_risk_score:.1f}")
    risk_breakdown = graph_state.metadata.get("risk_breakdown", {})
    if risk_breakdown:
        print(f"    Risk Decomposition:")
        total_risk = sum(risk_breakdown.values())
        for component, value in sorted(risk_breakdown.items(), key=lambda x: x[1], reverse=True):
            if total_risk > 0:
                percentage = (value / total_risk * 100)
                print(f"      - {component}: {value:.2f} ({percentage:.1f}%)")
            else:
                print(f"      - {component}: {value:.2f}")
    
    # === FIX 7: Enhanced Graph Health Metrics ===
    health_metrics = {
        "avg_node_risk": graph_state.metadata.get("avg_node_risk", 0.0),
        "avg_edge_persistence": graph_state.metadata.get("avg_edge_persistence", 0.0),
        "externality_ratio": graph_state.metadata.get("externality_ratio", 0.0),
        "infrastructure_ratio": graph_state.metadata.get("infrastructure_ratio", 0.0),
        "suspicious_edge_ratio": graph_state.metadata.get("suspicious_edge_ratio", 0.0),
        "community_balance_score": graph_state.metadata.get("community_balance_score", 0.0),
        "relationship_diversity_score": graph_state.metadata.get("relationship_diversity_score", 0.0),
        "external_dependency_score": graph_state.metadata.get("external_dependency_score", 0.0),
        "risk_concentration_score": graph_state.metadata.get("risk_concentration_score", 0.0),
    }
    
    if any(health_metrics.values()):
        print(f"\n    Graph Health Metrics:")
        print(f"      Avg Node Risk: {health_metrics['avg_node_risk']:.2f}")
        print(f"      Community Balance: {health_metrics['community_balance_score']:.2f}")
        print(f"      Relationship Diversity: {health_metrics['relationship_diversity_score']:.2f}")
        print(f"      External Dependency: {health_metrics['external_dependency_score']:.2f}")
        print(f"      Risk Concentration: {health_metrics['risk_concentration_score']:.2f}")
    
    # === FIX 1: High Behavioral Importance (Noise Suppressed) ===
    if graph_state.high_centrality_nodes:
        print(f"\n    Top Behavioral Importance:")
        for node_ip in graph_state.high_centrality_nodes:
            print(f"      - {node_ip}")
    
    # Relationship types
    if graph_state.relationship_types:
        print(f"\n    Relationship Types Detected:")
        for rel_type in sorted(graph_state.relationship_types)[:12]:
            print(f"      - {rel_type}")
    
    # === FIX 4: Event-Driven Snapshot Generation Statistics ===
    print(f"\n    Snapshot Statistics:")
    if temporal_snapshots:
        quality_scores = [snap.metadata.get("quality_score", 0.0) for snap in temporal_snapshots]
        quality_reasons = {}
        for snap in temporal_snapshots:
            reason = snap.metadata.get("quality_reason", "unknown")
            quality_reasons[reason] = quality_reasons.get(reason, 0) + 1
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        useful_count = quality_reasons.get("useful_snapshot", 0)
        redundant_count = quality_reasons.get("redundant_snapshot", 0)
        
        print(f"      Total Snapshots: {len(temporal_snapshots)}")
        print(f"      Meaningful Snapshots: {useful_count}")
        print(f"      Redundant Snapshots: {redundant_count}")
        print(f"      Average Quality Score: {avg_quality:.2f}")
        print(f"      Quality Distribution:")
        for reason in ["useful_snapshot", "moderate_snapshot", "sparse_snapshot", "redundant_snapshot", "empty_snapshot"]:
            count = quality_reasons.get(reason, 0)
            if count > 0:
                print(f"        • {reason}: {count}")
    else:
        print(f"      Total Snapshots: 0")
    
    # === FIX 8: Layer 5 Preparation (Lineage & Fingerprinting) ===
    fingerprint = graph_state.metadata.get("graph_fingerprint", "")
    if fingerprint:
        print(f"\n    Layer 5 Readiness:")
        print(f"      Graph Fingerprint: {fingerprint[:12]}...")
        print(f"      Snapshot Lineage: Ready for diff engine")
        print(f"      Graph Version: 1 (base state)")
    
    # Replay metadata
    print(f"\n    Replay Metadata:")
    print(f"      Deterministic ordering: Enabled")
    print(f"      Sequence range: {graph_state.replay_sequence_start} -> {graph_state.replay_sequence_end}")
    
    print()


def _parse_timestamp(timestamp: str) -> datetime:
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp.astimezone(timezone.utc)


if __name__ == "__main__":
    main()
