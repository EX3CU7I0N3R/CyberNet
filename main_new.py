"""
Graph-First Behavioral Network Analysis Platform

Pipeline:
  PCAP Packets
    |
  Canonical Events (normalized, enriched, directional)
    |
  Directional Flows (initiator/responder semantics preserved)
    |
  Enriched Flows (behavioral metrics with statistical gating)
    |
  Exports (CSV, NDJSON)
"""

import argparse
import pandas as pd
from datetime import datetime

from ingestion.parse import (
    parse_pcap,
    extract_packet_info,
    CanonicalEvent,
    events_to_ndjson,
)
from aggregation.flow_builder import (
    build_flows,
    flows_to_dataframe,
    DirectionalFlow,
)
from aggregation.flow_metrics import (
    compute_flow_metrics,
    EnrichedFlow,
)


def main():
    """Execute behavioral analysis pipeline."""
    
    parser = argparse.ArgumentParser(
        description="Graph-First Network Behavioral Analysis Platform"
    )
    
    parser.add_argument(
        "pcap_file",
        help="Path to the PCAP file to analyze"
    )
    
    parser.add_argument(
        "--ndjson-export",
        action="store_true",
        help="Export to NDJSON format (in addition to CSV)"
    )
    
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Skip CSV export"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("BEHAVIORAL NETWORK ANALYSIS PLATFORM")
    print("="*80 + "\n")
    
    # ========================================================================
    # STEP 1: PARSE PCAP
    # ========================================================================
    print("[*] STEP 1: Parsing PCAP file...")
    
    try:
        packets = parse_pcap(args.pcap_file)
        packet_count = len(packets)
        print(f"    [OK] Loaded {packet_count:,} packets\n")
    except Exception as e:
        print(f"    [ERROR] {e}\n")
        return
    
    # ========================================================================
    # STEP 2: NORMALIZE PACKETS -> CANONICAL EVENTS
    # ========================================================================
    print("[*] STEP 2: Normalizing packets to canonical events...")
    
    canonical_events = []
    failed_packets = 0
    
    for idx, packet in enumerate(packets):
        try:
            event = extract_packet_info(packet)
            if event:
                # Set packet index
                event.packet_index = idx
                canonical_events.append(event)
            else:
                failed_packets += 1
        except Exception:
            failed_packets += 1
    
    successful = len(canonical_events)
    print(f"    [OK] Normalized {successful:,} packets")
    if failed_packets > 0:
        print(f"    [WARN] Failed to parse {failed_packets:,} packets\n")
    else:
        print()
    
    if not canonical_events:
        print("    [ERROR] No valid packets to analyze\n")
        return
    
    # ========================================================================
    # STEP 3: BUILD DIRECTIONAL FLOWS
    # ========================================================================
    print("[*] STEP 3: Building directional flows...")
    print("    (Preserving initiator/responder semantics)\n")
    
    directional_flows = build_flows(canonical_events)
    flow_count = len(directional_flows)
    
    print(f"    [OK] Built {flow_count:,} directional flows")
    
    # Flow statistics
    total_bytes = sum(f.initiator_bytes + f.responder_bytes for f in directional_flows.values())
    total_duration = sum(f.duration_seconds for f in directional_flows.values())
    
    print(f"    [OK] Total traffic: {total_bytes:,} bytes")
    print(f"    [OK] Total duration: {total_duration:,.1f} seconds\n")
    
    # ========================================================================
    # STEP 4: COMPUTE BEHAVIORAL METRICS
    # ========================================================================
    print("[*] STEP 4: Computing behavioral metrics...")
    print("    (Statistical gating for beacon scoring)")
    print("    (Modular: statistics, timing, entropy, heuristics)\n")
    
    enriched_flows = compute_flow_metrics(canonical_events, directional_flows)
    
    # Beacon scoring statistics
    beacon_scored = sum(1 for f in enriched_flows if f.beacon_score is not None)
    gated = len(enriched_flows) - beacon_scored
    
    print(f"    [OK] Computed metrics for {flow_count:,} flows")
    print(f"    [OK] Beacon scoring: {beacon_scored:,} flows (sufficient data)")
    print(f"    [GATE] Beacon scoring: {gated:,} flows (gated - insufficient data)\n")
    
    # ========================================================================
    # STEP 5: ANALYSIS SUMMARY
    # ========================================================================
    print("[*] STEP 5: Analysis Summary\n")
    
    # Direction classification
    directions = {}
    for flow in enriched_flows:
        d = flow.direction
        directions[d] = directions.get(d, 0) + 1
    
    print("    Traffic Direction:")
    for direction, count in sorted(directions.items()):
        print(f"      - {direction:15s}: {count:>6,} flows")
    
    # Suspicious flows
    suspicious = [f for f in enriched_flows if f.is_suspicious]
    print(f"\n    Suspicious Flows: {len(suspicious)}")
    for flow in suspicious[:5]:  # Top 5
        print(f"      - {flow.initiator_ip}:{flow.initiator_port} -> {flow.responder_ip}:{flow.responder_port}")
        print(f"        Indicators: {', '.join(flow.suspicious_indicators)}")
    
    # Beacon-scored flows
    beacon_flows = [f for f in enriched_flows if f.beacon_score is not None and f.beacon_score > 0.5]
    if beacon_flows:
        print(f"\n    High Beacon Scores (potential periodic C2):")
        for flow in beacon_flows[:3]:  # Top 3
            print(f"      - {flow.initiator_ip}:{flow.initiator_port} -> {flow.responder_ip}:{flow.responder_port}")
            print(f"        Score: {flow.beacon_score:.2%} | Confidence: {flow.beacon_confidence:.2%} | Intervals: {flow.beacon_intervals}")
    
    print()
    
    # ========================================================================
    # STEP 6: EXPORT ARTIFACTS
    # ========================================================================
    print("[*] STEP 6: Exporting analysis artifacts...")
    
    # Export canonical events
    if not args.no_csv:
        canonical_df = pd.DataFrame([e.model_dump() for e in canonical_events])
        canonical_df.to_csv("normalized_packets.csv", index=False)
        print(f"    [OK] Wrote normalized_packets.csv ({len(canonical_df):,} rows)")
    
    if args.ndjson_export:
        events_to_ndjson(canonical_events, "normalized_packets.ndjson")
        print(f"    [OK] Wrote normalized_packets.ndjson ({len(canonical_events):,} events)")
    
    # Export flows
    if not args.no_csv:
        flows_df = flows_to_dataframe(directional_flows)
        flows_df.to_csv("flows.csv", index=False)
        print(f"    [OK] Wrote flows.csv ({len(flows_df):,} rows)")
    
    if args.ndjson_export:
        events_to_ndjson(list(directional_flows.values()), "flows.ndjson")
        print(f"    [OK] Wrote flows.ndjson ({flow_count:,} flows)")
    
    # Export enriched flows
    if not args.no_csv:
        enriched_df = pd.DataFrame([f.model_dump() for f in enriched_flows])
        enriched_df.to_csv("enriched_flows.csv", index=False)
        print(f"    [OK] Wrote enriched_flows.csv ({len(enriched_df):,} rows)")
    
    if args.ndjson_export:
        events_to_ndjson(enriched_flows, "enriched_flows.ndjson")
        print(f"    [OK] Wrote enriched_flows.ndjson ({len(enriched_flows):,} flows)")
    
    print()
    print("="*80)
    print("[SUCCESS] ANALYSIS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
