import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    name: str
    baseline: float
    noise: float = 0.0
    daily_swing: float = 0.0
    drift_per_hour: float = 0.0
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class Config:
    zones: dict[str, list[Metric]]
    tick_seconds: float
    driver: str


def load(path: str | None = None) -> Config:
    import yaml

    path = path or os.environ.get("CONFIG_PATH", "/etc/home-monitoring/zones.yaml")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw or "zones" not in raw:
        raise ValueError(f"{path}: missing top-level 'zones' key")

    zones: dict[str, list[Metric]] = {}
    for zone_name, metrics in raw["zones"].items():
        if not metrics:
            raise ValueError(f"zone '{zone_name}': no metrics defined")
        zones[zone_name] = [
            Metric(
                name=metric_name,
                baseline=float(params["baseline"]),
                noise=float(params.get("noise", 0.0)),
                daily_swing=float(params.get("daily_swing", 0.0)),
                drift_per_hour=float(params.get("drift_per_hour", 0.0)),
                minimum=params.get("minimum"),
                maximum=params.get("maximum"),
            )
            for metric_name, params in metrics.items()
        ]

    # Env var wins (lets docker-compose override per-deployment); falls back
    # to the yaml default, then a hardcoded default.
    tick_seconds = os.environ.get("TICK_SECONDS") or raw.get("tick_seconds", 5)

    return Config(
        zones=zones,
        tick_seconds=float(tick_seconds),
        driver=os.environ.get("DRIVER", "mock"),
    )
