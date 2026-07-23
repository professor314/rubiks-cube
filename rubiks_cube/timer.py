"""Rubik's cube solve timer.

Simple perf_counter-based timer for measuring solve times.
"""

from __future__ import annotations

import time


class CubeTimer:
    """Timer for Rubik's cube solves.

    Examples
    --------
    >>> timer = CubeTimer()
    >>> timer.start()
    >>> timer.is_running
    True
    >>> elapsed = timer.stop()
    >>> elapsed > 0
    True
    """

    def __init__(self) -> None:
        self._start_time: float | None = None
        self._stop_time: float | None = None

    @property
    def is_running(self) -> bool:
        """Whether the timer is currently active."""
        return self._start_time is not None and self._stop_time is None

    @property
    def elapsed(self) -> float:
        """Current or final elapsed time in seconds."""
        if self._start_time is None:
            return 0.0
        if self._stop_time is not None:
            return self._stop_time - self._start_time
        return time.perf_counter() - self._start_time

    def start(self) -> None:
        """Start the timer. Resets if previously used."""
        self._start_time = time.perf_counter()
        self._stop_time = None

    def stop(self) -> float:
        """Stop the timer and return elapsed seconds."""
        if not self.is_running:
            return 0.0
        self._stop_time = time.perf_counter()
        return self.elapsed

    def reset(self) -> None:
        """Reset the timer."""
        self._start_time = None
        self._stop_time = None
