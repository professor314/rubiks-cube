"""Solve statistics for Rubik's cube practice sessions.

Pure-Python (no numpy) so it is portable and easily testable. Implements the
standard speedcubing metrics used by the WCA community:

- **mean** of all solves
- **best** / **worst** single
- **ao5** (average of 5): drop the best and worst of the last 5, mean the rest
- **ao12** (average of 12): drop best and worst of the last 12, mean the rest

A "DNF" (did-not-finish) solve is represented by ``math.inf`` so it always
counts as the worst time and is dropped first in trimmed averages — matching
how cubers treat DNFs in an average.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Solve:
    """A single recorded solve.

    Parameters
    ----------
    time : float
        Solve time in seconds. Use ``math.inf`` for a DNF.
    scramble : str
        The scramble notation used for this solve.
    timestamp : float
        Unix timestamp when the solve was recorded.
    dnf : bool
        Whether the solve was a DNF (did not finish).
    """

    time: float
    scramble: str = ""
    timestamp: float = 0.0
    dnf: bool = False

    @property
    def effective_time(self) -> float:
        """Time used for ranking: ``inf`` for a DNF, else the raw time."""
        return math.inf if self.dnf else self.time

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-safe dict (``inf`` stored as the string 'inf')."""
        return {
            "time": "inf" if math.isinf(self.time) else self.time,
            "scramble": self.scramble,
            "timestamp": self.timestamp,
            "dnf": self.dnf,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Solve:
        """Rebuild a :class:`Solve` from :meth:`to_dict` output."""
        raw = d.get("time", 0.0)
        time_val = math.inf if raw == "inf" else float(raw)  # type: ignore[arg-type]
        return cls(
            time=time_val,
            scramble=str(d.get("scramble", "")),
            timestamp=float(d.get("timestamp", 0.0)),  # type: ignore[arg-type]
            dnf=bool(d.get("dnf", False)),
        )


def trimmed_average(times: list[float]) -> float:
    """Average after dropping the single best and single worst time.

    This is the WCA definition of an "average" (used for ao5/ao12). Requires
    at least 3 values so that something remains after trimming.

    Parameters
    ----------
    times : list[float]
        Effective solve times (``inf`` allowed for DNFs).

    Returns
    -------
    float
        The trimmed mean, or ``inf`` if more than one solve is a DNF (because
        trimming removes only one worst value).

    Raises
    ------
    ValueError
        If fewer than 3 times are supplied.
    """
    if len(times) < 3:
        raise ValueError("trimmed_average requires at least 3 times")
    ordered = sorted(times)
    middle = ordered[1:-1]
    if any(math.isinf(t) for t in middle):
        return math.inf
    return sum(middle) / len(middle)


@dataclass
class SolveStats:
    """Aggregates solves and computes speedcubing statistics.

    Examples
    --------
    >>> stats = SolveStats()
    >>> for t in [10.0, 12.0, 11.0, 9.0, 13.0]:
    ...     stats.add(Solve(time=t))
    >>> round(stats.best, 1)
    9.0
    >>> round(stats.ao5(), 1)  # drop 9.0 and 13.0 -> mean(10,11,12)
    11.0
    """

    solves: list[Solve] = field(default_factory=list)

    def add(self, solve: Solve) -> None:
        """Append a solve to the history."""
        self.solves.append(solve)

    @property
    def count(self) -> int:
        """Total number of recorded solves."""
        return len(self.solves)

    @property
    def best(self) -> float:
        """Best (lowest) effective time, or ``inf`` if no finished solves."""
        if not self.solves:
            return math.inf
        return min(s.effective_time for s in self.solves)

    @property
    def worst(self) -> float:
        """Worst (highest) effective time, or ``inf`` if none recorded."""
        if not self.solves:
            return math.inf
        return max(s.effective_time for s in self.solves)

    @property
    def mean(self) -> float:
        """Mean of all finished solves, or ``inf`` if any solve is a DNF.

        A single DNF makes the overall mean undefined (``inf``), consistent
        with how a session mean is reported when a DNF is present.
        """
        if not self.solves:
            return math.inf
        times = [s.effective_time for s in self.solves]
        if any(math.isinf(t) for t in times):
            return math.inf
        return sum(times) / len(times)

    def _ao(self, n: int) -> float:
        """Average over the last ``n`` solves (trimmed). ``inf`` if < n solves."""
        if self.count < n:
            return math.inf
        recent = [s.effective_time for s in self.solves[-n:]]
        return trimmed_average(recent)

    def ao5(self) -> float:
        """Average of the last 5 solves (best & worst dropped)."""
        return self._ao(5)

    def ao12(self) -> float:
        """Average of the last 12 solves (best & worst dropped)."""
        return self._ao(12)

    def best_ao5(self) -> float:
        """Best ao5 across every rolling window of 5 in the history."""
        return self._best_rolling_ao(5)

    def best_ao12(self) -> float:
        """Best ao12 across every rolling window of 12 in the history."""
        return self._best_rolling_ao(12)

    def _best_rolling_ao(self, n: int) -> float:
        if self.count < n:
            return math.inf
        times = [s.effective_time for s in self.solves]
        best = math.inf
        for i in range(len(times) - n + 1):
            window = times[i : i + n]
            avg = trimmed_average(window)
            best = min(best, avg)
        return best

    def to_dict(self) -> dict[str, object]:
        """Serialize the whole history to a JSON-safe dict."""
        return {"solves": [s.to_dict() for s in self.solves]}

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> SolveStats:
        """Rebuild :class:`SolveStats` from :meth:`to_dict` output."""
        raw_solves = d.get("solves", [])
        if not isinstance(raw_solves, list):
            raw_solves = []
        solves = [Solve.from_dict(s) for s in raw_solves]
        return cls(solves=solves)
