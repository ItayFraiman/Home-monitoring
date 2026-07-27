import httpx
from prometheus_client.parser import text_string_to_metric_families

_UNITS = {"celsius", "percent", "ratio", "seconds"}


def _base_metric(name: str) -> str:
    """sensor_soil_moisture_percent -> soil_moisture"""
    core = name.removeprefix("sensor_")
    head, _, tail = core.rpartition("_")
    return head if tail in _UNITS else core


def fetch_readings(base_url: str, timeout: float = 3.0) -> dict[str, dict[str, float]]:
    resp = httpx.get(f"{base_url}/metrics", timeout=timeout)
    resp.raise_for_status()

    readings: dict[str, dict[str, float]] = {}
    for family in text_string_to_metric_families(resp.text):
        if not family.name.startswith("sensor_"):
            continue
        base = _base_metric(family.name)
        for sample in family.samples:
            zone = sample.labels.get("zone")
            if zone is not None:
                readings.setdefault(zone, {})[base] = sample.value
    return readings