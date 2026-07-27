import logging

log = logging.getLogger("actuator.drivers")


class MockDriver:
    """Logs commands and remembers its own state. No hardware."""

    def __init__(self, device_id: str, **_options):
        self._device_id = device_id
        self._on = False

    def turn_on(self) -> None:
        log.info("device=%s driver=mock action=on", self._device_id)
        self._on = True

    def turn_off(self) -> None:
        log.info("device=%s driver=mock action=off", self._device_id)
        self._on = False

    def actual_state(self) -> bool:
        return self._on


def build(device):
    if device.driver == "mock":
        return MockDriver(device.device_id, **(device.options or {}))
    if device.driver == "gpio":
        from .gpio_driver import GpioDriver          # imported only if used
        return GpioDriver(device.device_id, **(device.options or {}))
    raise ValueError(f"device '{device.device_id}': unknown driver '{device.driver}'")