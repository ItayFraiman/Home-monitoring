import os
from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class DeviceConfig:
    device_id: str
    driver: str
    type: str
    min_off_seconds: float = 0.0
    max_runtime_seconds: float = 3600.0
    options: dict | None = None


def load(path: str | None = None) -> dict[str, DeviceConfig]:
    path = path or os.environ.get("DEVICES_PATH", "/etc/home-monitoring/devices.yaml")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw or "devices" not in raw:
        raise ValueError(f"{path}: missing top-level 'devices' key")

    known = {"driver", "type", "min_off_seconds", "max_runtime_seconds"}
    devices: dict[str, DeviceConfig] = {}

    for device_id, params in raw["devices"].items():
        if not params or "driver" not in params:
            raise ValueError(f"device '{device_id}': missing 'driver'")
        devices[device_id] = DeviceConfig(
            device_id=device_id,
            driver=params["driver"],
            type=params.get("type", "unknown"),
            min_off_seconds=float(params.get("min_off_seconds", 0.0)),
            max_runtime_seconds=float(params.get("max_runtime_seconds", 3600.0)),
            options={k: v for k, v in params.items() if k not in known},
        )

    return devices