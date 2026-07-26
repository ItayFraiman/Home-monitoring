import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel
from starlette.responses import Response

import config
import drivers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("actuator")

device_state = Gauge("actuator_device_state", "1 if the device reports itself on.", ["device", "type"])
commands_total = Counter("actuator_commands_total", "Commands received.", ["device", "command", "result"])
runtime_seconds = Counter("actuator_runtime_seconds_total", "Seconds each device has been on.", ["device"])
safety_stops = Counter("actuator_safety_stops_total", "Times a device was stopped by a safety rule.", ["device", "reason"])


class Device:
    def __init__(self, cfg):
        self.cfg = cfg
        self.driver = drivers.build(cfg)
        self.on_since: float | None = None
        self.off_since: float = time.monotonic()
        self.expires_at: float | None = None

    @property
    def is_on(self) -> bool:
        return self.driver.actual_state()

    def turn_on(self, duration_seconds: float | None) -> str:
        now = time.monotonic()

        if not self.is_on:
            waited = now - self.off_since
            if waited < self.cfg.min_off_seconds:
                return "blocked_min_off"
            self.driver.turn_on()
            self.on_since = now

        cap = self.cfg.max_runtime_seconds
        requested = duration_seconds if duration_seconds is not None else cap
        self.expires_at = (self.on_since or now) + min(requested, cap)
        return "ok"

    def turn_off(self, reason: str = "commanded") -> str:
        if self.is_on:
            self.driver.turn_off()
            if reason != "commanded":
                safety_stops.labels(device=self.cfg.device_id, reason=reason).inc()
            self.off_since = time.monotonic()
        self.on_since = None
        self.expires_at = None
        return "ok"


devices: dict[str, Device] = {}


async def supervise() -> None:
    """Closes anything whose time is up. This is the fail-safe."""
    last = time.monotonic()
    while True:
        await asyncio.sleep(1.0)
        now = time.monotonic()
        elapsed, last = now - last, now

        for device in devices.values():
            if device.is_on:
                runtime_seconds.labels(device=device.cfg.device_id).inc(elapsed)
                if device.expires_at is not None and now >= device.expires_at:
                    log.info("device=%s auto-closing", device.cfg.device_id)
                    device.turn_off(reason="expired")
            device_state.labels(
                device=device.cfg.device_id, type=device.cfg.type
            ).set(1 if device.is_on else 0)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for device_id, cfg in config.load().items():
        devices[device_id] = Device(cfg)
    log.info("loaded %d devices: %s", len(devices), ", ".join(devices))
    task = asyncio.create_task(supervise())
    yield
    task.cancel()
    for device in devices.values():
        device.turn_off(reason="shutdown")


app = FastAPI(lifespan=lifespan)


class OnRequest(BaseModel):
    duration_seconds: float | None = None


def _get(device_id: str) -> Device:
    if device_id not in devices:
        raise HTTPException(status_code=404, detail=f"unknown device '{device_id}'")
    return devices[device_id]


@app.post("/devices/{device_id}/on")
def turn_on(device_id: str, body: OnRequest):
    device = _get(device_id)
    result = device.turn_on(body.duration_seconds)
    commands_total.labels(device=device_id, command="on", result=result).inc()
    return {"device": device_id, "result": result, "actual_state": device.is_on}


@app.post("/devices/{device_id}/off")
def turn_off(device_id: str):
    device = _get(device_id)
    result = device.turn_off()
    commands_total.labels(device=device_id, command="off", result=result).inc()
    return {"device": device_id, "result": result, "actual_state": device.is_on}


@app.get("/devices")
def list_devices():
    return {
        device_id: {
            "type": device.cfg.type,
            "actual_state": device.is_on,
            "expires_in": (
                round(device.expires_at - time.monotonic(), 1)
                if device.expires_at else None
            ),
        }
        for device_id, device in devices.items()
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok", "devices": len(devices)}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)