import pyshark
import hashlib
from pydantic import BaseModel

# FOr a given Pcap file, parse 
def parse_pcap(file_path: str):
    """Parse a PCAP file and return a list of packets."""
    cap = pyshark.FileCapture(file_path)
    return cap

#for the given packects, extract minimal field 
def extract_packet_info(packet):
    """Extract relevant information from a packet."""
    try:
        return {
            'timestamp': packet.sniff_time,
            'src_ip': packet.ip.src,
            'dst_ip': packet.ip.dst,
            'src_port': packet[packet.transport_layer].srcport,
            'dst_port': packet[packet.transport_layer].dstport,
            'protocol': packet.transport_layer,
            'length': int(packet.length)
        }
    except AttributeError:
        return None
    
#For a list of packets, normalize protoco names 
def normalize_protocol(protocol):
    """Normalize protocol names to standard format."""
    protocol = protocol.upper()
    if protocol in ['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS', 'FTP', 'SSH','DNS']:
        return protocol.lower()
    
# Direction Classification
def classify_direction(src_ip, dst_ip, local_network_prefix='192.168.'):
    """Classify traffic direction based on IP addresses."""
    if src_ip.startswith(local_network_prefix) and not dst_ip.startswith(local_network_prefix):
        return 'outbound'
    elif not src_ip.startswith(local_network_prefix) and dst_ip.startswith(local_network_prefix):
        return 'inbound'
    else:
        return 'internal'

#generate stable flow ids
def generate_flow_id(src_ip, dst_ip, src_port, dst_port, protocol):
    """Generate a stable flow ID based on packet attributes."""
    flow_key = f"{src_ip}:{src_port}->{dst_ip}:{dst_port}({protocol})"
    return hashlib.md5(flow_key.encode()).hexdigest()

# Convert to pydantic model
class NetworkEvent(BaseModel):
    timestamp: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    length: int
    direction: str
    flow_id: str

# output NDJSON
def output_ndjson(events, output_file):
    """Output a list of NetworkEvent objects to an NDJSON file."""
    with open(output_file, 'w') as f:
        for event in events:
            f.write(event.json() + '\n')