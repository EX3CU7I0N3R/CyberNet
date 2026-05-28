from collections import defaultdict
from statistics import mean, stdev
from math import log2
from datetime import datetime


def compute_flow_metrics(events, flows):
    """
    Compute behavioral metrics for each flow.

    Returns:
        List of enriched flow records.
    """

    # Group packets by flow_id
    packets_by_flow = defaultdict(list)

    for event in events:
        packets_by_flow[event["flow_id"]].append(event)

    enriched_flows = []

    for flow in flows:

        flow_id = flow["flow_id"]

        packets = packets_by_flow.get(flow_id, [])

        timestamps = []
        packet_sizes = []

        for pkt in packets:

            timestamps.append(
                parse_timestamp(pkt["timestamp"])
            )

            packet_sizes.append(
                pkt["bytes"]
            )

        timestamps.sort()

        # Compute inter-arrival times
        inter_arrivals = []

        for i in range(1, len(timestamps)):

            delta = (
                timestamps[i] - timestamps[i - 1]
            ).total_seconds()

            inter_arrivals.append(delta)

        # Duration safety
        duration = max(
            flow["duration_seconds"],
            0.0001
        )

        # Metrics
        packets_per_second = (
            flow["packet_count"] / duration
        )

        bytes_per_second = (
            flow["total_bytes"] / duration
        )

        average_packet_size = (
            mean(packet_sizes)
            if packet_sizes
            else 0
        )

        packet_size_stddev = (
            stdev(packet_sizes)
            if len(packet_sizes) > 1
            else 0
        )

        inter_arrival_mean = (
            mean(inter_arrivals)
            if inter_arrivals
            else 0
        )

        inter_arrival_stddev = (
            stdev(inter_arrivals)
            if len(inter_arrivals) > 1
            else 0
        )

        entropy = calculate_entropy(packet_sizes)

        burst_score = calculate_burst_score(
            packets_per_second,
            inter_arrival_stddev
        )

        beacon_score = calculate_beacon_score(
            inter_arrival_mean,
            inter_arrival_stddev
        )

        enriched_flow = {

            **flow,

            "packets_per_second": round(
                packets_per_second, 4
            ),

            "bytes_per_second": round(
                bytes_per_second, 4
            ),

            "average_packet_size": round(
                average_packet_size, 2
            ),

            "packet_size_stddev": round(
                packet_size_stddev, 2
            ),

            "inter_arrival_mean": round(
                inter_arrival_mean, 4
            ),

            "inter_arrival_stddev": round(
                inter_arrival_stddev, 4
            ),

            "packet_size_entropy": round(
                entropy, 4
            ),

            "burst_score": round(
                burst_score, 4
            ),

            "beacon_score": round(
                beacon_score, 4
            )
        }

        enriched_flows.append(enriched_flow)

    return enriched_flows


def calculate_entropy(values):
    """
    Shannon entropy of packet sizes.
    """

    if not values:
        return 0

    total = len(values)

    frequencies = defaultdict(int)

    for value in values:
        frequencies[value] += 1

    entropy = 0

    for count in frequencies.values():

        probability = count / total

        entropy -= probability * log2(probability)

    return entropy


def calculate_burst_score(
    packets_per_second,
    inter_arrival_stddev
):
    """
    Estimate burstiness.

    Higher:
        more aggressive traffic spikes.
    """

    return (
        packets_per_second *
        (1 + inter_arrival_stddev)
    )


def calculate_beacon_score(
    inter_arrival_mean,
    inter_arrival_stddev
):
    """
    Estimate periodic beacon behavior.

    Lower stddev relative to mean
    suggests consistent beaconing.
    """

    if inter_arrival_mean == 0:
        return 0

    consistency = 1 - min(
        inter_arrival_stddev /
        inter_arrival_mean,
        1
    )

    return max(consistency, 0)


def parse_timestamp(timestamp):

    if isinstance(timestamp, datetime):
        return timestamp

    return datetime.fromisoformat(
        str(timestamp)
    )