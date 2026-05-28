import pyshark
import hashlib
from pydantic import BaseModel
import ipaddress


# FOr a given Pcap file, parse 
def parse_pcap(file_path: str):
    """Parse a PCAP file and return a list of packets."""
    cap = pyshark.FileCapture(file_path)
    return cap

def detect_application_protocol(packet):

    try:

        highest = packet.highest_layer.upper()

        protocol_map = {
            "HTTP": "http",
            "TLS": "https",
            "SSL": "https",
            "DNS": "dns",
            "SMB": "smb",
            "FTP": "ftp",
            "SSH": "ssh",
            "SMTP": "smtp",
            "ICMP": "icmp"
        }

        return protocol_map.get(highest, "unknown")

    except:
        return "unknown"

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
            'application_protocol': detect_application_protocol(packet),
            'transport': packet.transport_layer,
            'bytes': int(packet.length)
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
import ipaddress

LOCAL_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

def is_internal(ip):
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in net for net in LOCAL_NETWORKS)
    except:
        return False

def classify_direction(src_ip, dst_ip):
    src_internal = is_internal(src_ip)
    dst_internal = is_internal(dst_ip)

    if src_internal and not dst_internal:
        return "outbound"

    elif not src_internal and dst_internal:
        return "inbound"

    elif src_internal and dst_internal:
        return "internal"

    return "external"

#generate stable flow ids
def generate_flow_id(src_ip, dst_ip, src_port, dst_port, protocol):

    endpoints = sorted([
        f"{src_ip}:{src_port}",
        f"{dst_ip}:{dst_port}"
    ])

    flow_key = f"{endpoints[0]}-{endpoints[1]}-{protocol}"

    return hashlib.md5(flow_key.encode()).hexdigest()


# Convert to pydantic model
class NetworkEvent(BaseModel):
    packet_id: str
    timestamp: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    application_protocol: str
    transport: str
    bytes: int
    direction: str
    flow_id: str

# output NDJSON
def output_ndjson(events, output_file):
    """Output a list of NetworkEvent objects to an NDJSON file."""
    with open(output_file, 'w') as f:
        for event in events:
            f.write(event.json() + '\n')