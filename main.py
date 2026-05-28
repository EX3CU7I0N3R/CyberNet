import argparse
import pandas as pd

from ingestion.parse import *

from aggregation.flow_builder import build_flows
from aggregation.flow_metrics import compute_flow_metrics


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Graph-First Network Behavioral Analysis Platform"
    )

    parser.add_argument(
        "pcap_file",
        help="Path to the PCAP file to analyze"
    )

    args = parser.parse_args()

    print("\n[+] Parsing PCAP...\n")

    # ---------------------------------------------------
    # Step 1 — Parse PCAP
    # ---------------------------------------------------

    packets = parse_pcap(args.pcap_file)

    # ---------------------------------------------------
    # Step 2 — Normalize Packets
    # ---------------------------------------------------

    packet_info_list = []

    for idx, packet in enumerate(packets):

        info = extract_packet_info(packet)

        if not info:
            continue

        # Normalize transport
        transport = normalize_protocol(
            info["transport"]
        )

        # Application protocol detection
        application_protocol = detect_application_protocol(
            packet
        )

        # Direction classification
        direction = classify_direction(
            info["src_ip"],
            info["dst_ip"]
        )

        # Stable bidirectional flow ID
        flow_id = generate_flow_id(
            info["src_ip"],
            info["dst_ip"],
            info["src_port"],
            info["dst_port"],
            transport
        )

        normalized_event = {

            "packet_index": idx,

            "timestamp": str(info["timestamp"]),

            "src_ip": info["src_ip"],
            "src_port": int(info["src_port"]),

            "dst_ip": info["dst_ip"],
            "dst_port": int(info["dst_port"]),

            "transport": transport,

            "application_protocol": application_protocol,

            "bytes": int(info["bytes"]),

            "direction": direction,

            "flow_id": flow_id
        }

        packet_info_list.append(
            normalized_event
        )

    print(
        f"[+] Normalized {len(packet_info_list)} packets"
    )

    # ---------------------------------------------------
    # Step 3 — Convert to DataFrame
    # ---------------------------------------------------

    packet_df = pd.DataFrame(packet_info_list)

    print("\n[+] Packet Events Preview:\n")

    print(packet_df.head())

    # ---------------------------------------------------
    # Step 4 — Build Flows
    # ---------------------------------------------------

    print("\n[+] Building flows...\n")

    flows = build_flows(packet_info_list)

    print(
        f"[+] Generated {len(flows)} flows"
    )

    flow_df = pd.DataFrame(flows)

    print("\n[+] Flow Preview:\n")

    print(flow_df.head())

    # ---------------------------------------------------
    # Step 5 — Compute Behavioral Metrics
    # ---------------------------------------------------

    print("\n[+] Computing flow metrics...\n")

    enriched_flows = compute_flow_metrics(
        packet_info_list,
        flows
    )

    enriched_df = pd.DataFrame(
        enriched_flows
    )

    print("\n[+] Enriched Flow Metrics:\n")

    print(
        enriched_df[
            [
                "flow_id",
                "packet_count",
                "total_bytes",
                "duration_seconds",
                "packets_per_second",
                "bytes_per_second",
                "beacon_score",
                "burst_score"
            ]
        ].head()
    )

    # ---------------------------------------------------
    # Step 6 — Export Artifacts
    # ---------------------------------------------------

    print("\n[+] Exporting analysis artifacts...\n")

    packet_df.to_csv(
        "normalized_packets.csv",
        index=False
    )

    flow_df.to_csv(
        "flows.csv",
        index=False
    )

    enriched_df.to_csv(
        "enriched_flows.csv",
        index=False
    )

    print("[+] Export complete")

    print("\n[✓] Layer 2 Complete\n")