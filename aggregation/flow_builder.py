from collections import defaultdict
from datetime import datetime


def build_flows(events):
    """
    Aggregate normalized packet events into flow-level records.
    """

    flows = defaultdict(lambda: {
        "flow_id": None,

        "src_ip": None,
        "src_port": None,

        "dst_ip": None,
        "dst_port": None,

        "transport": None,
        "application_protocols": set(),

        "packet_count": 0,
        "total_bytes": 0,

        "first_seen": None,
        "last_seen": None,

        "directions": set()
    })

    for event in events:

        flow_id = event["flow_id"]

        flow = flows[flow_id]

        # Static metadata
        flow["flow_id"] = flow_id

        flow["src_ip"] = event["src_ip"]
        flow["src_port"] = event["src_port"]

        flow["dst_ip"] = event["dst_ip"]
        flow["dst_port"] = event["dst_port"]

        flow["transport"] = event["transport"]

        # Aggregated metadata
        flow["application_protocols"].add(
            event["application_protocol"]
        )

        flow["packet_count"] += 1

        flow["total_bytes"] += event["bytes"]

        flow["directions"].add(event["direction"])

        # Timestamp handling
        ts = parse_timestamp(event["timestamp"])

        if flow["first_seen"] is None or ts < flow["first_seen"]:
            flow["first_seen"] = ts

        if flow["last_seen"] is None or ts > flow["last_seen"]:
            flow["last_seen"] = ts

    # Finalize flow records
    finalized_flows = []

    for flow in flows.values():

        duration = (
            flow["last_seen"] - flow["first_seen"]
        ).total_seconds()

        finalized_flows.append({

            "flow_id": flow["flow_id"],

            "src_ip": flow["src_ip"],
            "src_port": flow["src_port"],

            "dst_ip": flow["dst_ip"],
            "dst_port": flow["dst_port"],

            "transport": flow["transport"],

            "application_protocols": list(
                flow["application_protocols"]
            ),

            "packet_count": flow["packet_count"],

            "total_bytes": flow["total_bytes"],

            "first_seen": flow["first_seen"].isoformat(),

            "last_seen": flow["last_seen"].isoformat(),

            "duration_seconds": duration,

            "directions": list(flow["directions"])
        })

    return finalized_flows


def parse_timestamp(timestamp):
    """
    Normalize timestamp parsing.
    """

    if isinstance(timestamp, datetime):
        return timestamp

    return datetime.fromisoformat(str(timestamp))