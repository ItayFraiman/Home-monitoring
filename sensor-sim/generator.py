"""Deterministic-ish fake sensor readings.

Each metric is built from up to three components, all optional so a metric
with only `baseline` set just returns a flat line:

- daily_swing: a 24h cosine cycle, peaking mid-afternoon (~15:00 local
  server time) and troughing overnight -- close enough to how outdoor
  temperature and indoor humidity actually move to be useful in a demo.
- drift_per_hour: a linear trend since the process started (soil moisture
  drying out over time is the motivating case).
- noise: gaussian jitter so the line isn't perfectly smooth.
"""

import math
import random
from datetime import datetime

from config import Metric


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def reading(metric: Metric, now: datetime, hours_since_start: float) -> float:
    value = metric.baseline

    if metric.daily_swing:
        hour_of_day = now.hour + now.minute / 60 + now.second / 3600
        phase = (hour_of_day - 15) / 24 * 2 * math.pi
        value += (metric.daily_swing / 2) * math.cos(phase)

    if metric.drift_per_hour:
        value += metric.drift_per_hour * hours_since_start

    if metric.noise:
        value += random.gauss(0, metric.noise)

    return value
