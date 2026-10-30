"""Tests for the pure-Python solve statistics module."""

from __future__ import annotations

import math

from rubiks_cube.stats import Solve, SolveStats, trimmed_average


def test_trimmed_average_basic() -> None:
    # drop best(9) and worst(13) -> mean(10,11,12) == 11
    assert trimmed_average([10.0, 12.0, 11.0, 9.0, 13.0]) == 11.0


def test_trimmed_average_requires_three() -> None:
    try:
        trimmed_average([1.0, 2.0])
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_trimmed_average_single_dnf_dropped() -> None:
    # one inf is the worst and gets trimmed away
    assert trimmed_average([10.0, 11.0, 12.0, 13.0, math.inf]) == 12.0


def test_trimmed_average_two_dnf_is_inf() -> None:
    # two infs -> one survives trimming -> inf
    assert math.isinf(trimmed_average([10.0, 11.0, math.inf, math.inf, 12.0]))


def test_best_worst_mean() -> None:
    stats = SolveStats()
    for t in (10.0, 12.0, 11.0):
        stats.add(Solve(time=t))
    assert stats.best == 10.0
    assert stats.worst == 12.0
    assert stats.mean == 11.0
    assert stats.count == 3


def test_mean_with_dnf_is_inf() -> None:
    stats = SolveStats()
    stats.add(Solve(time=10.0))
    stats.add(Solve(time=0.0, dnf=True))
    assert math.isinf(stats.mean)


def test_ao5_needs_five() -> None:
    stats = SolveStats()
    for t in (10.0, 11.0, 12.0, 13.0):
        stats.add(Solve(time=t))
    assert math.isinf(stats.ao5())
    stats.add(Solve(time=14.0))
    # drop 10 and 14 -> mean(11,12,13) == 12
    assert stats.ao5() == 12.0


def test_ao12() -> None:
    stats = SolveStats()
    for t in range(1, 13):  # 1..12
        stats.add(Solve(time=float(t)))
    # drop 1 and 12 -> mean(2..11) == 6.5
    assert stats.ao12() == 6.5


def test_best_rolling_ao5() -> None:
    stats = SolveStats()
    # a fast window near the start, slower later
    for t in (5.0, 5.0, 5.0, 5.0, 5.0, 20.0, 21.0, 22.0):
        stats.add(Solve(time=t))
    assert stats.best_ao5() == 5.0


def test_solve_round_trip_serialization() -> None:
    s = Solve(time=12.34, scramble="U R' F2", timestamp=1000.0, dnf=False)
    assert Solve.from_dict(s.to_dict()) == s


def test_dnf_serialization_round_trip() -> None:
    s = Solve(time=math.inf, scramble="D2 L", timestamp=5.0, dnf=True)
    restored = Solve.from_dict(s.to_dict())
    assert restored.dnf is True
    assert math.isinf(restored.time)


def test_stats_round_trip_serialization() -> None:
    stats = SolveStats()
    stats.add(Solve(time=10.0, scramble="U"))
    stats.add(Solve(time=math.inf, dnf=True))
    restored = SolveStats.from_dict(stats.to_dict())
    assert restored.count == 2
    assert restored.solves[0].time == 10.0
    assert restored.solves[1].dnf is True


def test_empty_stats_defaults() -> None:
    stats = SolveStats()
    assert stats.count == 0
    assert math.isinf(stats.best)
    assert math.isinf(stats.ao5())
