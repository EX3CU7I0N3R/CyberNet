from behavior.role_manager import infer_host_role as _infer_host_role


def infer_host_role(metrics: dict, state: dict) -> tuple[str, float, list[str]]:
    role_result = _infer_host_role(metrics, state)
    return (
        role_result["role"],
        role_result["confidence"],
        role_result["supporting_signals"],
    )
