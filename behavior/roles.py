INFRASTRUCTURE_PROTOCOLS = {"arp", "dhcp", "llmnr", "mdns", "nbns", "ssdp"}
SERVER_PORTS = {53, 80, 88, 135, 139, 389, 443, 445, 464, 636, 3389}
DOMAIN_CONTROLLER_PORTS = {53, 88, 135, 389, 445, 464, 636}


def infer_host_role(metrics: dict, state: dict) -> tuple[str, float, list[str]]:
    protocols = set(metrics["protocols"])
    inbound_ratio = metrics["inbound_ratio"]
    responded_count = metrics["responded_flow_count"]
    unique_ports = metrics["unique_ports"]
    service_ports = state["service_ports"]
    evidence = []

    if protocols and protocols.issubset(INFRASTRUCTURE_PROTOCOLS):
        evidence.append("infrastructure_protocol_only")
        return "infrastructure_device", 0.78, evidence

    if protocols & {"mdns", "ssdp"} and metrics["external_connections"] == 0:
        evidence.append("local_discovery_service")
        return "multicast_service_host", 0.70, evidence

    dc_overlap = len(service_ports & DOMAIN_CONTROLLER_PORTS)
    if dc_overlap >= 4 and {"dns", "smb", "kerberos", "ldap"} & protocols:
        evidence.append("domain_service_port_mix")
        return "domain_controller", 0.68, evidence

    server_overlap = len(service_ports & SERVER_PORTS)
    if responded_count >= 10 and inbound_ratio >= 0.35 and server_overlap >= 2:
        evidence.append("service_responder_behavior")
        return "server", 0.64, evidence

    if metrics["outbound_ratio"] >= 0.45 and metrics["unique_destinations"] >= 3:
        evidence.append("client_initiated_fanout")
        return "workstation", 0.62, evidence

    if unique_ports <= 2 and responded_count > metrics["initiated_flow_count"]:
        evidence.append("narrow_responder_profile")
        return "server", 0.50, evidence

    return "unknown", 0.35, ["insufficient_role_evidence"]
