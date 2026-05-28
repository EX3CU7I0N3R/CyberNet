import os
import argparse
import pandas as pd
from collections import defaultdict

try:
    from scapy.all import rdpcap, IP, TCP, UDP
except ImportError:
    rdpcap = None
    IP = None
    TCP = None
    UDP = None


def read_pcap(file_path):
    """Read a .pcap file and return packets."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"PCAP file not found: {file_path}")
    if rdpcap is None:
        raise ImportError("Scapy is required to read pcap files. Install it with: pip install scapy")
    return rdpcap(file_path)


def summarize_packets(packets):
    return [packet.summary() for packet in packets]

def normalize_packet(packet):
    """Normalize a packet for consistent processing. {  "timestamp": "",  "src_ip": "",  "dst_ip": "",  "protocol": "",  "bytes": 0,  "direction": "","flow_id": ""} """
    
    return packet

def extract_network_flows(packets):
    """
    Extract network flows from packets and return as DataFrame.
    Columns: src_ip, dst_ip, src_port, dst_port, protocol, bytes_sent, packet_count
    """
    flows = defaultdict(lambda: {'packet_count': 0, 'bytes_sent': 0, 'protocol': None})
    
    for packet in packets:
        try:
            if IP in packet:
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                protocol = packet[IP].proto
                packet_size = len(packet)
                
                src_port = None
                dst_port = None
                
                if TCP in packet:
                    src_port = packet[TCP].sport
                    dst_port = packet[TCP].dport
                    protocol_name = 'TCP'
                elif UDP in packet:
                    src_port = packet[UDP].sport
                    dst_port = packet[UDP].dport
                    protocol_name = 'UDP'
                else:
                    protocol_name = 'Other'
                
                # Create flow key (bidirectional)
                flow_key = tuple(sorted([
                    (src_ip, src_port),
                    (dst_ip, dst_port)
                ]))
                
                flows[flow_key]['packet_count'] += 1
                flows[flow_key]['bytes_sent'] += packet_size
                flows[flow_key]['protocol'] = protocol_name
                flows[flow_key]['src_ip'] = src_ip
                flows[flow_key]['dst_ip'] = dst_ip
                flows[flow_key]['src_port'] = src_port
                flows[flow_key]['dst_port'] = dst_port
        except Exception as e:
            continue
    
    # Convert to DataFrame
    flow_list = []
    for flow_key, flow_data in flows.items():
        flow_list.append({
            'src_ip': flow_data['src_ip'],
            'dst_ip': flow_data['dst_ip'],
            'src_port': flow_data['src_port'],
            'dst_port': flow_data['dst_port'],
            'protocol': flow_data['protocol'],
            'bytes_sent': flow_data['bytes_sent'],
            'packet_count': flow_data['packet_count']
        })
    
    return pd.DataFrame(flow_list) if flow_list else pd.DataFrame()


