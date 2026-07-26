from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    action: str            # "on" | "off" | "none"
    duration_seconds: float | None = None
    reason: str = ""


def evaluate(rule, readings: dict[str, float], device_on: bool) -> Decision:
    if rule.type == "threshold":
        return _threshold(rule, readings, device_on)
    if rule.type == "hysteresis":
        return _hysteresis(rule, readings, device_on)
    return Decision("none", reason=f"unknown type {rule.type}")


def _threshold(rule, readings, device_on) -> Decision:
    if device_on:
        return Decision("none", reason="already running")

    for metric, cond in rule.conditions.items():
        value = readings.get(metric)
        if value is None:
            return Decision("none", reason=f"no reading for {metric}")
        if "below" in cond and not value < cond["below"]:
            return Decision("none", reason=f"{metric}={value:.1f} not below {cond['below']}")
        if "above" in cond and not value > cond["above"]:
            return Decision("none", reason=f"{metric}={value:.1f} not above {cond['above']}")

    return Decision("on", duration_seconds=rule.duration_seconds, reason="all conditions met")


def _hysteresis(rule, readings, device_on) -> Decision:
    value = readings.get(rule.metric)
    if value is None:
        return Decision("none", reason=f"no reading for {rule.metric}")

    if not device_on and value > rule.on_above:
        return Decision("on", reason=f"{rule.metric}={value:.1f} > {rule.on_above}")
    if device_on and value < rule.off_below:
        return Decision("off", reason=f"{rule.metric}={value:.1f} < {rule.off_below}")

    return Decision("none", reason="within deadband")