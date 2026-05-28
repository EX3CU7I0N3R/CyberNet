from typing import Optional


PORT_PROTOCOLS = {
    "tcp": {
        20: ("ftp_data", 0.62),
        21: ("ftp", 0.68),
        22: ("ssh", 0.72),
        25: ("smtp", 0.68),
        53: ("dns", 0.64),
        80: ("http", 0.72),
        110: ("pop", 0.66),
        123: ("ntp", 0.62),
        135: ("msrpc", 0.70),
        139: ("netbios_session", 0.70),
        143: ("imap", 0.66),
        389: ("ldap", 0.70),
        443: ("https", 0.74),
        445: ("smb", 0.74),
        465: ("smtps", 0.68),
        587: ("smtp_submission", 0.66),
        636: ("ldaps", 0.70),
        993: ("imaps", 0.68),
        995: ("pops", 0.68),
        3389: ("rdp", 0.74),
    },
    "udp": {
        53: ("dns", 0.78),
        67: ("dhcp", 0.86),
        68: ("dhcp", 0.86),
        123: ("ntp", 0.72),
        137: ("nbns", 0.86),
        138: ("netbios_datagram", 0.80),
        161: ("snmp", 0.70),
        162: ("snmptrap", 0.68),
        1900: ("ssdp", 0.86),
        5353: ("mdns", 0.88),
        5355: ("llmnr", 0.88),
    },
}


def enrich_application_protocol(packet, transport_layer: str, src_port: Optional[int], dst_port: Optional[int]) -> dict:
    layer_match = _layer_protocol(packet)
    metadata = _extract_metadata(packet)

    if layer_match["application_protocol"] != "unknown":
        layer_match["protocol_evidence"].extend(metadata["protocol_evidence"])
        layer_match.update(metadata)
        return layer_match

    port_match = _port_protocol(transport_layer, src_port, dst_port)
    port_match["protocol_evidence"].extend(metadata["protocol_evidence"])
    port_match.update(metadata)
    return port_match


def _layer_protocol(packet) -> dict:
    layer_map = {
        "HTTP": ("http", 0.96),
        "HTTP2": ("http2", 0.92),
        "TLS": ("https", 0.92),
        "SSL": ("https", 0.86),
        "DNS": ("dns", 0.96),
        "MDNS": ("mdns", 0.96),
        "NBNS": ("nbns", 0.96),
        "LLMNR": ("llmnr", 0.96),
        "SSDP": ("ssdp", 0.96),
        "DHCP": ("dhcp", 0.96),
        "BOOTP": ("dhcp", 0.96),
        "ARP": ("arp", 0.96),
        "SMB": ("smb", 0.92),
        "NBSS": ("smb", 0.86),
        "KERBEROS": ("kerberos", 0.92),
        "LDAP": ("ldap", 0.88),
        "ICMP": ("icmp", 0.95),
    }

    try:
        highest_layer = packet.highest_layer.upper()
    except Exception:
        highest_layer = ""

    protocol, confidence = layer_map.get(highest_layer, ("unknown", 0.0))
    evidence = [f"decoded_layer:{highest_layer.lower()}"] if protocol != "unknown" else []
    return {
        "application_protocol": protocol,
        "app_confidence": confidence,
        "protocol_evidence": evidence,
        "protocol_enrichment": "decoded_layer" if evidence else "none",
    }


def _port_protocol(transport_layer: str, src_port: Optional[int], dst_port: Optional[int]) -> dict:
    port_map = PORT_PROTOCOLS.get(transport_layer, {})
    for port in (dst_port, src_port):
        if port in port_map:
            protocol, confidence = port_map[port]
            return {
                "application_protocol": protocol,
                "app_confidence": confidence,
                "protocol_evidence": [f"well_known_port:{transport_layer}/{port}"],
                "protocol_enrichment": "port_inference",
            }

    if transport_layer == "arp":
        return {
            "application_protocol": "arp",
            "app_confidence": 0.96,
            "protocol_evidence": ["transport:arp"],
            "protocol_enrichment": "transport_inference",
        }
    if transport_layer == "icmp":
        return {
            "application_protocol": "icmp",
            "app_confidence": 0.95,
            "protocol_evidence": ["transport:icmp"],
            "protocol_enrichment": "transport_inference",
        }

    return {
        "application_protocol": "unknown",
        "app_confidence": 0.0,
        "protocol_evidence": [],
        "protocol_enrichment": "none",
    }


def _extract_metadata(packet) -> dict:
    metadata = {
        "tls_sni": None,
        "tls_alpn": None,
        "http_host": None,
        "dns_query": None,
        "protocol_evidence": [],
    }

    tls_layer = _safe_layer(packet, "TLS") or _safe_layer(packet, "SSL")
    if tls_layer:
        metadata["tls_sni"] = _first_attr(tls_layer, ("handshake_extensions_server_name", "server_name"))
        metadata["tls_alpn"] = _first_attr(tls_layer, ("handshake_extensions_alpn_str", "app_layer_protocol"))
        if metadata["tls_sni"]:
            metadata["protocol_evidence"].append("tls_sni")
        if metadata["tls_alpn"]:
            metadata["protocol_evidence"].append("tls_alpn")

    http_layer = _safe_layer(packet, "HTTP")
    if http_layer:
        metadata["http_host"] = _first_attr(http_layer, ("host", "request_full_uri"))
        if metadata["http_host"]:
            metadata["protocol_evidence"].append("http_host")

    dns_layer = _safe_layer(packet, "DNS")
    if dns_layer:
        metadata["dns_query"] = _first_attr(dns_layer, ("qry_name", "resp_name"))
        if metadata["dns_query"]:
            metadata["protocol_evidence"].append("dns_query")

    return metadata


def _safe_layer(packet, layer_name: str):
    try:
        if layer_name in packet:
            return packet[layer_name]
    except Exception:
        return None
    return None


def _first_attr(layer, field_names: tuple[str, ...]) -> Optional[str]:
    for field_name in field_names:
        value = getattr(layer, field_name, None)
        if value:
            return str(value)
    return None
