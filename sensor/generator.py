import math
import random
from datetime import datetime

SECONDS_PER_DAY = 86_400


def _daily_cycle(at: datetime) -> float:
    """-1.0 at ~04:00, +1.0 at ~16:00. Peak heat is late afternoon, not noon."""
    seconds = at.hour * 3600 + at.minute * 60 + at.second
    phase = (seconds / SECONDS_PER_DAY) * 2 * math.pi
    return math.sin(phase - math.pi / 2 - (4 / 24) * 2 * math.pi)


def reading(metric, at: datetime, hours_since_start: float = 0.0, rng=random) -> float:
    """Pure: same inputs (with a seeded rng) give the same output."""
    value = metric.baseline
    value += metric.daily_swing * _daily_cycle(at)
    value += metric.drift_per_hour * hours_since_start
    if metric.noise:
        value += rng.gauss(0.0, metric.noise)
    return value


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))