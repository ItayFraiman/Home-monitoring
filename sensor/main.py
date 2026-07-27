import logging
import os
import signal
import threading
import time
from datetime import datetime, timezone

from prometheus_client import Counter, Gauge, start_http_server

import config
from generator import clamp, reading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("sensor")

# Prometheus convention: metric names carry their unit as a suffix.
UNITS = {
    "temperature": "celsius",
    "soil_moisture": "percent",
    "humidity": "percent",
}

ticks_total = Counter(
    "sensor_ticks_total",
    "Number of completed read cycles.",
)

shutdown = threading.Event()


def _handle_signal(signum, _frame):
    log.info("received signal %s, shutting down", signal.Signals(signum).name)
    shutdown.set()


def build_gauges(cfg: config.Config) -> dict[str, Gauge]:
    """One Gauge per distinct metric name, labelled by zone. Created once."""
    gauges: dict[str, Gauge] = {}
    for metrics in cfg.zones.values():
        for metric in metrics:
            if metric.name in gauges:
                continue
            unit = UNITS.get(metric.name)
            full_name = f"sensor_{metric.name}_{unit}" if unit else f"sensor_{metric.name}"
            gauges[metric.name] = Gauge(
                full_name,
                f"Simulated {metric.name.replace('_', ' ')} reading.",
                ["zone"],
            )
    return gauges


def tick(cfg: config.Config, gauges: dict[str, Gauge], hours_elapsed: float) -> None:
    now = datetime.now(timezone.utc)
    for zone_name, metrics in cfg.zones.items():
        for metric in metrics:
            value = reading(metric, now, hours_since_start=hours_elapsed)
            if metric.minimum is not None or metric.maximum is not None:
                value = clamp(
                    value,
                    metric.minimum if metric.minimum is not None else float("-inf"),
                    metric.maximum if metric.maximum is not None else float("inf"),
                )
            gauges[metric.name].labels(zone=zone_name).set(value)


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    cfg = config.load()
    log.info("loaded %d zones, driver=%s", len(cfg.zones), cfg.driver)

    gauges = build_gauges(cfg)

    port = int(os.environ.get("METRICS_PORT", "8000"))
    start_http_server(port)
    log.info("serving metrics on :%d", port)

    started = time.monotonic()
    while not shutdown.is_set():
        hours_elapsed = (time.monotonic() - started) / 3600
        tick(cfg, gauges, hours_elapsed)
        ticks_total.inc()
        shutdown.wait(cfg.tick_seconds)

    log.info("stopped cleanly")


if __name__ == "__main__":
    main()