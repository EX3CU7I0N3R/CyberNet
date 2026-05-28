
import argparse
import pandas as pd
from ingestion.parse import read_pcap, summarize_packets, extract_network_flows
from models.ratModel import RATDetectionModel


def analyze_rat_behavior(flows_df):
    """
    Analyze network flows for RAT behavior.
    Returns list of detected RAT activities.
    """
    if flows_df.empty:
        return []
    
    rat_detector = RATDetectionModel()
    detected_rats = []
    
    # Analyze each potential victim-attacker pair
    # Group by flows to identify suspicious patterns
    for src_ip in flows_df['src_ip'].unique():
        for dst_ip in flows_df['dst_ip'].unique():
            if src_ip != dst_ip:
                # Get flows for this pair
                pair_flows = flows_df[
                    ((flows_df['src_ip'] == src_ip) & (flows_df['dst_ip'] == dst_ip)) |
                    ((flows_df['src_ip'] == dst_ip) & (flows_df['dst_ip'] == src_ip))
                ].copy()
                
                if not pair_flows.empty:
                    # Assume the source with more data sent is potential victim
                    victim_ip = src_ip
                    attacker_ip = dst_ip
                    
                    # Run RAT detection
                    is_rat, confidence = rat_detector.detect_rat(
                        victim_ip=victim_ip,
                        victim_mac="unknown",
                        victim_name=f"Host-{victim_ip.split('.')[-1]}",
                        attacker_ip=attacker_ip,
                        transactions=pair_flows
                    )
                    
                    if is_rat or confidence > 0.4:  # Flag suspicious activity
                        detected_rats.append({
                            'victim_ip': victim_ip,
                            'attacker_ip': attacker_ip,
                            'is_rat': is_rat,
                            'confidence': confidence,
                            'summary': rat_detector.get_detection_summary()
                        })
    
    return detected_rats


def print_rat_findings(findings):
    """Print RAT detection findings in readable format."""
    if not findings:
        print("\n[RAT DETECTION] No suspicious RAT behavior detected.")
        return
    
    print(f"\n[RAT DETECTION] Found {len(findings)} potential RAT indicators:\n")
    
    for idx, finding in enumerate(findings, 1):
        print(f"{'='*70}")
        print(f"Alert #{idx}")
        print(f"{'='*70}")
        print(f"Victim IP:        {finding['victim_ip']}")
        print(f"Attacker IP:      {finding['attacker_ip']}")
        print(f"Is RAT:           {finding['is_rat']}")
        print(f"Confidence Score: {finding['confidence']:.2%}")
        
        summary = finding['summary']
        print(f"Transaction Count: {summary['transaction_count']}")
        
        if summary['transaction_count'] > 0:
            print(f"\nTop Transactions:")
            for trans in summary['transactions'][:5]:
                print(f"  - {trans}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read a .pcap file and analyze for RAT malware behavior.")
    parser.add_argument("pcap", help="Path to the .pcap file", default="sample.pcap", nargs='?')
    parser.add_argument("--summary-only", action="store_true", help="Print only packet summaries")
    args = parser.parse_args()

    print(f"[*] Reading PCAP file: {args.pcap}")
    packets = read_pcap(args.pcap)
    print(f"[*] Loaded {len(packets)} packets\n")
    
    if args.summary_only:
        print("[*] Packet Summaries:")
        for summary in summarize_packets(packets):
            print(f"  {summary}")
    else:
        # Extract network flows for RAT analysis
        print("[*] Extracting network flows...")
        flows_df = extract_network_flows(packets)
        print(f"[*] Identified {len(flows_df)} unique network flows\n")
        
        # Analyze for RAT behavior
        print("[*] Analyzing for RAT malware behavior...")
        rat_findings = analyze_rat_behavior(flows_df)
        
        # Print findings
        print_rat_findings(rat_findings)
        
        # Print flow statistics
        print(f"\n[FLOW STATISTICS]")
        print(f"{'='*70}")
        print(f"Total Flows:      {len(flows_df)}")
        if not flows_df.empty:
            print(f"Total Bytes Sent: {flows_df['bytes_sent'].sum():,}")
            print(f"Avg Bytes/Flow:   {flows_df['bytes_sent'].mean():,.0f}")
            print(f"Avg Packets/Flow: {flows_df['packet_count'].mean():,.1f}")