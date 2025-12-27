# helpers.py
from typing import Optional
import time

def _now() -> float:
    return time.time()

def _ema(prev: Optional[float], value: float, alpha: float) -> float:
    if prev is None:
        return value
    return alpha * value + (1 - alpha) * prev
