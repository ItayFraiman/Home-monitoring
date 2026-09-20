import httpx


def list_devices(base_url: str, timeout: float = 3.0) -> set[str]:
    resp = httpx.get(f"{base_url}/devices", timeout=timeout)
    resp.raise_for_status()
    return set(resp.json().keys())


def fetch_states(base_url: str, timeout: float = 3.0) -> dict[str, bool]:
    resp = httpx.get(f"{base_url}/devices", timeout=timeout)
    resp.raise_for_status()
    return {device: info["actual_state"] for device, info in resp.json().items()}


def send_on(base_url, device, duration_seconds, timeout: float = 3.0) -> str:
    payload = {"duration_seconds": duration_seconds} if duration_seconds is not None else {}
    resp = httpx.post(f"{base_url}/devices/{device}/on", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["result"]


def send_off(base_url, device, timeout: float = 3.0) -> str:
    resp = httpx.post(f"{base_url}/devices/{device}/off", timeout=timeout)
    resp.raise_for_status()
    return resp.json()["result"]