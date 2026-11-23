"""Tests for session persistence and daily scrambles (pure-Python)."""

from __future__ import annotations

import json
from datetime import date
from itertools import pairwise
from pathlib import Path

from rubiks_cube.session import SessionStore, scramble_of_the_day
from rubiks_cube.stats import Solve, SolveStats


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "nope.json")
    stats = store.load()
    assert isinstance(stats, SolveStats)
    assert stats.count == 0


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "stats.json")
    stats = SolveStats()
    stats.add(Solve(time=12.0, scramble="U R'"))
    stats.add(Solve(time=10.5, scramble="F2 D"))
    store.save(stats)

    loaded = store.load()
    assert loaded.count == 2
    assert loaded.best == 10.5
    assert loaded.solves[0].scramble == "U R'"


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "deep" / "nested" / "stats.json")
    store.save(SolveStats())
    assert (tmp_path / "deep" / "nested" / "stats.json").exists()


def test_load_corrupt_file_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "stats.json"
    p.write_text("{ this is not valid json ", encoding="utf-8")
    store = SessionStore(p)
    assert store.load().count == 0


def test_load_non_dict_json_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "stats.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    store = SessionStore(p)
    assert store.load().count == 0


def test_save_is_atomic_no_temp_left(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "stats.json")
    store.save(SolveStats())
    leftovers = list(tmp_path.glob(".stats-*.tmp"))
    assert leftovers == []


def test_scramble_of_the_day_is_deterministic() -> None:
    a = scramble_of_the_day(date(2026, 1, 1))
    b = scramble_of_the_day(date(2026, 1, 1))
    assert a == b


def test_scramble_of_the_day_differs_by_date() -> None:
    a = scramble_of_the_day(date(2026, 1, 1))
    b = scramble_of_the_day(date(2026, 1, 2))
    assert a != b


def test_scramble_length_and_no_repeat_face() -> None:
    scramble = scramble_of_the_day(date(2026, 3, 14), length=25)
    tokens = scramble.split()
    assert len(tokens) == 25
    faces = [t[0] for t in tokens]
    for prev, nxt in pairwise(faces):
        assert prev != nxt


def test_scramble_tokens_valid() -> None:
    tokens = scramble_of_the_day(date(2026, 5, 5)).split()
    valid_faces = set("UDLRFB")
    for t in tokens:
        assert t[0] in valid_faces
        assert t[1:] in ("", "'", "2")
