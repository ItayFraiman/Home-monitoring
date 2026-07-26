import logging
import os
import signal
import threading
import time

from prometheus_client import Counter, Gauge, start_http_server

import actuator_client
import config
import rules as rules_engine
import sensor_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("controller")

evaluations = Counter("controller_evaluations_total", "Rule evaluations.", ["rule", "decision"])
commands = Counter("controller_commands_total", "Commands sent.", ["device", "command", "result"])
errors = Counter("controller_errors_total", "Errors by stage.", ["stage"])
ticks = Counter("controller_ticks_total", "Completed control cycles.")
seen = Gauge("controller_last_reading", "Last reading the controller saw.", ["zone", "metric"])

shutdown = threading.Event()


def _handle_signal(signum, _frame):
    log.info("signal %s, shutting down", signal.Signals(signum).name)
    shutdown.set()


def run_cycle(cfg: config.Config) -> None:
    try:
        readings = sensor_client.fetch_readings(cfg.sensor_url)
    except Exception as exc:
        errors.labels(stage="sensor_fetch").inc()
        log.warning("sensor fetch failed: %s", exc)
        return

    for zone, metrics in readings.items():
        for metric, value in metrics.items():
            seen.labels(zone=zone, metric=metric).set(value)

    try:
        states = actuator_client.fetch_states(cfg.actuator_url)
    except Exception as exc:
        errors.labels(stage="actuator_fetch").inc()
        log.warning("actuator state fetch failed: %s", exc)
        return

    for rule in cfg.rules:
        device_on = states.get(rule.device, False)
        decision = rules_engine.evaluate(rule, readings.get(rule.zone, {}), device_on)
        evaluations.labels(rule=rule.name, decision=decision.action).inc()

        if decision.action == "none":
            log.debug("rule=%s noop: %s", rule.name, decision.reason)
            continue

        try:
            if decision.action == "on":
                result = actuator_client.send_on(cfg.actuator_url, rule.device, decision.duration_seconds)
            else:
                result = actuator_client.send_off(cfg.actuator_url, rule.device)
            commands.labels(device=rule.device, command=decision.action, result=result).inc()
            log.info("rule=%s -> %s %s (%s) result=%s",
                     rule.name, decision.action, rule.device, decision.reason, result)
        except Exception as exc:
            errors.labels(stage="command").inc()
            log.warning("command failed rule=%s device=%s: %s", rule.name, rule.device, exc)


def validate_join(cfg: config.Config, attempts: int = 15) -> None:
    """Fail loudly at startup if a rule names a device that doesn't exist."""
    for i in range(attempts):
        try:
            known = actuator_client.list_devices(cfg.actuator_url)
            break
        except Exception as exc:
            log.info("waiting for actuator (%d/%d): %s", i + 1, attempts, exc)
            time.sleep(2)
    else:
        raise RuntimeError("actuator unreachable at startup")

    missing = sorted({r.device for r in cfg.rules if r.device not in known})
    if missing:
        raise RuntimeError(f"rules reference unknown devices: {missing}")
    log.info("validated %d rules against %d devices", len(cfg.rules), len(known))


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    cfg = config.load()
    start_http_server(int(os.environ.get("METRICS_PORT", "8000")))
    log.info("loaded %d rules, sensor=%s actuator=%s",
             len(cfg.rules), cfg.sensor_url, cfg.actuator_url)

    validate_join(cfg)

    while not shutdown.is_set():
        run_cycle(cfg)
        ticks.inc()
        shutdown.wait(cfg.eval_interval_seconds)

    log.info("stopped cleanly")


if __name__ == "__main__":
    main()