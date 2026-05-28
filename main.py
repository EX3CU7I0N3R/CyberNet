
import argparse
import pandas as pd
from ingestion.parse import *


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PCAP to RAT Detection Model")
    parser.add_argument("pcap_file", help="Path to the PCAP file to analyze")
    args = parser.parse_args()

    # Step 1: Parse the PCAP file
    packets = parse_pcap(args.pcap_file)

    # Step 2: Extract packet information and build a DataFrame
    packet_info_list = []
    for packet in packets:
        info = extract_packet_info(packet)
        if info:
            info['protocol'] = normalize_protocol(info['protocol'])
            info['direction'] = classify_direction(info['src_ip'], info['dst_ip'])
            info['flow_id'] = generate_flow_id(info['src_ip'], info['dst_ip'], 
                                               info['src_port'], info['dst_port'], 
                                               info['protocol'])
            packet_info_list.append(info)

    df = pd.DataFrame(packet_info_list)
    print(df.head())
