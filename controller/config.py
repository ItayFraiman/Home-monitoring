import os
from dataclasses import dataclass, field

import yaml


@dataclass(frozen=True)
class Rule:
    name: str
    zone: str
    type: str
    device: str
    metric: str | None = None
    on_above: float | None = None
    off_below: float | None = None
    duration_seconds: float | None = None
    conditions: dict | None = None


@dataclass(frozen=True)
class Config:
    sensor_url: str
    actuator_url: str
    eval_interval_seconds: float
    rules: list[Rule]


def load(path: str | None = None) -> Config:
    path = path or os.environ.get("RULES_PATH", "/etc/home-monitoring/rules.yaml")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw or "rules" not in raw:
        raise ValueError(f"{path}: missing top-level 'rules' key")

    rules: list[Rule] = []
    for entry in raw["rules"]:
        rule = Rule(**entry)
        _validate(rule)
        rules.append(rule)

    return Config(
        sensor_url=os.environ.get("SENSOR_URL", "http://sensor:8000").rstrip("/"),
        actuator_url=os.environ.get("ACTUATOR_URL", "http://actuator:8000").rstrip("/"),
        eval_interval_seconds=float(os.environ.get("EVAL_INTERVAL_SECONDS", "10")),
        rules=rules,
    )


def _validate(rule: Rule) -> None:
    if rule.type == "threshold":
        if not rule.conditions:
            raise ValueError(f"rule '{rule.name}': threshold needs 'conditions'")
        if rule.duration_seconds is None:
            raise ValueError(f"rule '{rule.name}': threshold needs 'duration_seconds'")
    elif rule.type == "hysteresis":
        missing = [f for f in ("metric", "on_above", "off_below") if getattr(rule, f) is None]
        if missing:
            raise ValueError(f"rule '{rule.name}': hysteresis needs {missing}")
        if rule.off_below >= rule.on_above:
            raise ValueError(f"rule '{rule.name}': off_below must be < on_above (no deadband)")
    else:
        raise ValueError(f"rule '{rule.name}': unknown type '{rule.type}'")