"""Accumulate observed charging energy without counting session resets twice."""

from dataclasses import dataclass, field
from math import isfinite

MAX_SESSIONS = 32


def valid_energy(value) -> bool:
    """Accept finite, nonnegative measured values, excluding booleans."""
    return (
        isinstance(value, (float, int))
        and not isinstance(value, bool)
        and isfinite(value)
        and value >= 0
    )


@dataclass
class EnergyCounter:
    """Keep a bounded per-session high-water mark and a persistent kWh total.

    The first reading establishes a baseline, rather than allocating energy
    delivered before installation to the current statistics interval. Subsequent
    sessions contribute their first reading in full, even if it exceeds the last
    session's reading. Lower or repeated readings never reduce or inflate totals.
    """

    total: float = 0.0
    sessions: dict[str, float] = field(default_factory=dict)

    @property
    def initialized(self) -> bool:
        return bool(self.sessions)

    def update(self, session_id, value) -> None:
        if (
            not isinstance(session_id, str)
            or not session_id
            or len(session_id) > 128
            or not valid_energy(value)
        ):
            return
        if not self.initialized:
            self.sessions[session_id] = float(value)
            return
        previous = self.sessions.get(session_id, 0.0)
        if value < previous:
            return
        self.total = round(self.total + value - previous, 6)
        self.sessions.pop(session_id, None)
        self.sessions[session_id] = float(value)
        if len(self.sessions) > MAX_SESSIONS:
            del self.sessions[next(iter(self.sessions))]

    def as_dict(self) -> dict:
        return {"version": 1, "total": self.total, "sessions": dict(self.sessions)}

    def restore(self, data) -> None:
        if not isinstance(data, dict) or data.get("version") != 1:
            return
        total, sessions = data.get("total"), data.get("sessions")
        if (
            not valid_energy(total)
            or not isinstance(sessions, dict)
            or not 1 <= len(sessions) <= MAX_SESSIONS
            or any(
                not isinstance(key, str) or not key or len(key) > 128 or not valid_energy(value)
                for key, value in sessions.items()
            )
        ):
            return
        self.total = float(total)
        self.sessions = dict(sessions)
