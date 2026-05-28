import hashlib
import ipaddress
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pyshark
from pydantic import BaseModel, Field


class IPClassification:
    RESERVED_RANGES = {
        "loopback": ipaddress.ip_network("127.0.0.0/8"),
        "link_local": ipaddress.ip_network("169.254.0.0/16"),
        "broadcast": ipaddress.ip_network("255.255.255.255/32"),
        "this_network": ipaddress.ip_network("0.0.0.0/8"),
        "multicast": ipaddress.ip_network("224.0.0.0/4"),
        "reserved": ipaddress.ip_network("240.0.0.0/4"),
    }

    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    ]

    @staticmethod
    def classify(ip_str: str) -> str:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return "error"

        for special_type, network in IPClassification.RESERVED_RANGES.items():
            if ip_obj in network:
                return special_type

        for network in IPClassification.PRIVATE_RANGES:
            if ip_obj in network:
                return "internal"

        return "external"


def classify_direction(src_ip: str, dst_ip: str) -> str:
    src_class = IPClassification.classify(src_ip)
    dst_class = IPClassification.classify(dst_ip)

    if src_class == "error" or dst_class == "error":
        return "error"
    if dst_class == "broadcast":
        return "broadcast"
    if dst_class == "multicast":
        return "multicast"
    if src_class == "loopback" or dst_class == "loopback":
        return "loopback"
    if src_class == "internal" and dst_class == "internal":
        return "internal"
    if src_class == "external" and dst_class == "external":
        return "external"
    if src_class == "internal" and dst_class == "external":
        return "outbound"
    if src_class == "external" and dst_class == "internal":
        return "inbound"

    return "unknown"


class TCPFlags:
    FLAG_FIELDS = {
        "syn": ("flags_syn", "SYN"),
        "ack": ("flags_ack", "ACK"),
        "rst": ("flags_reset", "RST"),
        "fin": ("flags_fin", "FIN"),
        "psh": ("flags_push", "PSH"),
        "urg": ("flags_urg", "URG"),
        "ece": ("flags_ece", "ECE"),
        "cwr": ("flags_cwr", "CWR"),
    }

    @staticmethod
    def extract(packet) -> Dict[str, bool]:
        flags = {flag: False for flag in TCPFlags.FLAG_FIELDS}

        try:
            tcp_layer = packet["TCP"]
        except Exception:
            return flags

        flags_text = str(getattr(tcp_layer, "flags", "")).upper()
        for flag, (field_name, label) in TCPFlags.FLAG_FIELDS.items():
            flags[flag] = label in flags_text or str(getattr(tcp_layer, field_name, "0")) == "1"

        return flags


class ProtocolInference:
    TRANSPORT_LAYER = {
        "TCP": "tcp",
        "UDP": "udp",
        "ICMP": "icmp",
        "IGMP": "igmp",
        "ARP": "arp",
    }

    APP_PROTOCOL_MAP = {
        "HTTP": ("http", 0.95),
        "HTTPS": ("https", 0.95),
        "TLS": ("https", 0.90),
        "SSL": ("https", 0.85),
        "DNS": ("dns", 0.95),
        "MDNS": ("mdns", 0.95),
        "NBNS": ("nbns", 0.95),
        "LLMNR": ("llmnr", 0.95),
        "SSDP": ("ssdp", 0.95),
        "DHCP": ("dhcp", 0.95),
        "BOOTP": ("dhcp", 0.95),
        "ARP": ("arp", 0.95),
        "SMB": ("smb", 0.90),
        "NBSS": ("smb", 0.85),
        "FTP": ("ftp", 0.90),
        "SSH": ("ssh", 0.95),
        "TELNET": ("telnet", 0.90),
        "SMTP": ("smtp", 0.90),
        "POP": ("pop", 0.90),
        "IMAP": ("imap", 0.90),
        "KERBEROS": ("kerberos", 0.95),
        "LDAP": ("ldap", 0.90),
        "ICMP": ("icmp", 0.95),
    }

    UDP_PORT_PROTOCOLS = {
        53: ("dns", 0.75),
        67: ("dhcp", 0.85),
        68: ("dhcp", 0.85),
        137: ("nbns", 0.85),
        1900: ("ssdp", 0.85),
        5353: ("mdns", 0.85),
        5355: ("llmnr", 0.85),
    }

    TCP_PORT_PROTOCOLS = {
        22: ("ssh", 0.70),
        25: ("smtp", 0.70),
        80: ("http", 0.70),
        110: ("pop", 0.70),
        143: ("imap", 0.70),
        443: ("https", 0.70),
        445: ("smb", 0.70),
    }

    @staticmethod
    def infer_transport(packet) -> str:
        try:
            if "IP" in packet:
                proto = packet["IP"].proto
                if proto == "6":
                    return "tcp"
                if proto == "17":
                    return "udp"
                if proto == "1":
                    return "icmp"
        except Exception:
            pass

        try:
            highest = packet.highest_layer.upper()
            return ProtocolInference.TRANSPORT_LAYER.get(highest, "unknown")
        except Exception:
            return "unknown"

    @staticmethod
    def infer_application(packet, transport_layer: str, src_port: Optional[int], dst_port: Optional[int]) -> tuple[str, float]:
        try:
            highest = packet.highest_layer.upper()
            if highest in ProtocolInference.APP_PROTOCOL_MAP:
                return ProtocolInference.APP_PROTOCOL_MAP[highest]
        except Exception:
            pass

        port_map = (
            ProtocolInference.UDP_PORT_PROTOCOLS
            if transport_layer == "udp"
            else ProtocolInference.TCP_PORT_PROTOCOLS
        )
        for port in (dst_port, src_port):
            if port in port_map:
                return port_map[port]

        if transport_layer == "arp":
            return "arp", 0.95
        if transport_layer == "icmp":
            return "icmp", 0.95

        return "unknown", 0.0


class CanonicalEvent(BaseModel):
    packet_index: int
    replay_sequence_id: int = 0
    timeline_index: int = 0
    timestamp: str
    src_ip: str
    dst_ip: str
    ttl: Optional[int] = None
    transport_layer: str
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    tcp_flags: Dict[str, bool] = Field(default_factory=dict)
    payload_bytes: int
    total_bytes: int
    application_protocol: str
    app_confidence: float
    direction: str
    flow_id: str


def parse_pcap(file_path: str):
    try:
        return pyshark.FileCapture(file_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"PCAP file not found: {file_path}")
    except Exception as exc:
        raise RuntimeError(f"Failed to parse PCAP: {exc}") from exc


def normalize_timestamp(timestamp: Any) -> str:
    if isinstance(timestamp, datetime):
        parsed_timestamp = timestamp
    else:
        parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))

    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

    return parsed_timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_packet_info(packet) -> Optional[CanonicalEvent]:
    try:
        timestamp = normalize_timestamp(
            packet.sniff_time if hasattr(packet, "sniff_time") else datetime.now(timezone.utc)
        )
        total_bytes = int(packet.length)

        if "IP" in packet:
            return _extract_ip_event(packet, timestamp, total_bytes)
        if "ARP" in packet:
            return _extract_arp_event(packet, timestamp, total_bytes)

        return None
    except Exception:
        return None


def _extract_ip_event(packet, timestamp: str, total_bytes: int) -> Optional[CanonicalEvent]:
    ip_layer = packet["IP"]
    src_ip = ip_layer.src
    dst_ip = ip_layer.dst
    ttl = int(ip_layer.ttl) if hasattr(ip_layer, "ttl") else None
    transport_layer = ProtocolInference.infer_transport(packet)

    src_port = None
    dst_port = None
    tcp_flags = {}

    if transport_layer == "tcp" and "TCP" in packet:
        tcp_layer = packet["TCP"]
        src_port = int(tcp_layer.srcport)
        dst_port = int(tcp_layer.dstport)
        tcp_flags = TCPFlags.extract(packet)
    elif transport_layer == "udp" and "UDP" in packet:
        udp_layer = packet["UDP"]
        src_port = int(udp_layer.srcport)
        dst_port = int(udp_layer.dstport)

    payload_bytes = _estimate_payload_bytes(total_bytes, transport_layer)
    app_protocol, app_confidence = ProtocolInference.infer_application(
        packet, transport_layer, src_port, dst_port
    )

    return CanonicalEvent(
        packet_index=0,
        replay_sequence_id=0,
        timeline_index=0,
        timestamp=timestamp,
        src_ip=src_ip,
        dst_ip=dst_ip,
        ttl=ttl,
        transport_layer=transport_layer,
        src_port=src_port,
        dst_port=dst_port,
        tcp_flags=tcp_flags,
        payload_bytes=payload_bytes,
        total_bytes=total_bytes,
        application_protocol=app_protocol,
        app_confidence=app_confidence,
        direction=classify_direction(src_ip, dst_ip),
        flow_id=generate_flow_id(src_ip, dst_ip, src_port or 0, dst_port or 0, transport_layer),
    )


def _extract_arp_event(packet, timestamp: str, total_bytes: int) -> Optional[CanonicalEvent]:
    arp_layer = packet["ARP"]
    src_ip = getattr(arp_layer, "src_proto_ipv4", "0.0.0.0")
    dst_ip = getattr(arp_layer, "dst_proto_ipv4", "255.255.255.255")

    return CanonicalEvent(
        packet_index=0,
        replay_sequence_id=0,
        timeline_index=0,
        timestamp=timestamp,
        src_ip=src_ip,
        dst_ip=dst_ip,
        ttl=None,
        transport_layer="arp",
        src_port=None,
        dst_port=None,
        tcp_flags={},
        payload_bytes=0,
        total_bytes=total_bytes,
        application_protocol="arp",
        app_confidence=0.95,
        direction=classify_direction(src_ip, dst_ip),
        flow_id=generate_flow_id(src_ip, dst_ip, 0, 0, "arp"),
    )


def _estimate_payload_bytes(total_bytes: int, transport_layer: str) -> int:
    header_bytes = 20
    if transport_layer == "tcp":
        header_bytes += 20
    elif transport_layer == "udp":
        header_bytes += 8
    return max(0, total_bytes - header_bytes)


def generate_flow_id(src_ip: str, dst_ip: str, src_port: int, dst_port: int, protocol: str) -> str:
    flow_key = f"{src_ip}:{src_port}->{dst_ip}:{dst_port}({protocol})"
    return hashlib.md5(flow_key.encode()).hexdigest()[:16]


def events_to_ndjson(events: list, output_file: str):
    with open(output_file, "w", encoding="utf-8") as output:
        for event in events:
            if isinstance(event, BaseModel):
                output.write(event.model_dump_json() + "\n")
            elif isinstance(event, dict):
                output.write(json.dumps(event, default=str) + "\n")
            else:
                output.write(json.dumps(event, default=str) + "\n")


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


def output_ndjson(events, output_file):
    with open(output_file, "w", encoding="utf-8") as output:
        for event in events:
            output.write(event.model_dump_json() + "\n")
