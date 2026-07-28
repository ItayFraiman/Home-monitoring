import os
from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class MetricConfig:
    name: str
    baseline: float
    daily_swing: float = 0.0
    drift_per_hour: float = 0.0
    noise: float = 0.0
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class Config:
    tick_seconds: int
    driver: str
    zones: dict[str, list[MetricConfig]]


def load(path: str | None = None) -> Config:
    path = path or os.environ.get("CONFIG_PATH", "/etc/home-monitoring/zones.yaml")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw or "zones" not in raw:
        raise ValueError(f"{path}: missing top-level 'zones' key")

    zones: dict[str, list[MetricConfig]] = {}
    for zone_name, metrics in raw["zones"].items():
        if not metrics:
            raise ValueError(f"zone '{zone_name}' has no metrics")
        zones[zone_name] = [
            MetricConfig(name=metric_name, **params)
            for metric_name, params in metrics.items()
        ]

    return Config(
        tick_seconds=int(os.environ.get("TICK_SECONDS", raw.get("tick_seconds", 5))),
        driver=os.environ.get("DRIVER", "mock"),
        zones=zones,
    )