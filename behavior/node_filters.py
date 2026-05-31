from __future__ import annotations

import ipaddress
from typing import Any


def is_non_investigative_node(node_or_ip: Any) -> bool:
    ip_text = getattr(node_or_ip, "ip_address", node_or_ip)
    try:
        ip_address = ipaddress.ip_address(str(ip_text))
    except ValueError:
        return False

    if ip_address.is_multicast:
        return True
    if str(ip_address) in {"0.0.0.0", "255.255.255.255"}:
        return True
    if ip_address.version == 4 and str(ip_address).endswith(".255"):
        return True
    return False
