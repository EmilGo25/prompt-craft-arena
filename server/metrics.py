"""A tiny in-process metrics registry — no external dependency.

Supports labeled counters, gauges, and simple sum/count "summaries" (enough to
read an average latency). Renders Prometheus text so a ``/metrics`` endpoint can
expose it. This is the observability the objective pool is driven by: the
pool-miss counter is the core SLI (a miss = a game that had to draw its target
live), and the demand counter feeds any later forecasting.

Single-threaded asyncio doesn't strictly need the lock, but it's cheap insurance
if metrics are ever touched from a thread executor.
"""

from __future__ import annotations

import threading
from collections import defaultdict

# A label set, normalized to a sorted tuple so {a,b} and {b,a} are one series.
_Labels = tuple[tuple[str, str], ...]


def _key(labels: dict[str, str]) -> _Labels:
    return tuple(sorted(labels.items()))


def _render_labels(labels: _Labels) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in labels)
    return "{" + inner + "}"


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, _Labels], float] = defaultdict(float)
        self._gauges: dict[tuple[str, _Labels], float] = {}
        # name -> [sum, count]; average = sum / count.
        self._summaries: dict[tuple[str, _Labels], list[float]] = defaultdict(
            lambda: [0.0, 0.0]
        )

    # -- writes -------------------------------------------------------------
    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._counters[(name, _key(labels))] += value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._gauges[(name, _key(labels))] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            s = self._summaries[(name, _key(labels))]
            s[0] += value
            s[1] += 1.0

    # -- reads (for /health JSON and tests) ---------------------------------
    def get_counter(self, name: str, **labels: str) -> float:
        with self._lock:
            return self._counters.get((name, _key(labels)), 0.0)

    def get_gauge(self, name: str, **labels: str) -> float | None:
        with self._lock:
            return self._gauges.get((name, _key(labels)))

    def get_average(self, name: str, **labels: str) -> float | None:
        with self._lock:
            s = self._summaries.get((name, _key(labels)))
            if not s or s[1] == 0:
                return None
            return s[0] / s[1]

    # -- render -------------------------------------------------------------
    def render(self) -> str:
        """Prometheus text exposition format."""
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                lines.append(f"{name}{_render_labels(labels)} {value}")
            for (name, labels), value in sorted(self._gauges.items()):
                lines.append(f"{name}{_render_labels(labels)} {value}")
            for (name, labels), (total, count) in sorted(self._summaries.items()):
                rl = _render_labels(labels)
                lines.append(f"{name}_sum{rl} {total}")
                lines.append(f"{name}_count{rl} {count}")
        return "\n".join(lines) + "\n"
