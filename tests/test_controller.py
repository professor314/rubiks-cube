"""Tests for the CubeController (undo/redo/scramble/reset).

Constructing a controller requires the numpy-backed engine, so these skip
without numpy and run fully in CI.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from rubiks_cube.controller import CubeController
from rubiks_cube.moves import Move


def test_starts_solved() -> None:
    c = CubeController()
    assert c.is_solved()
    assert not c.can_undo()
    assert not c.can_redo()


def test_apply_and_undo_restores() -> None:
    c = CubeController()
    c.apply(Move.R)
    assert not c.is_solved()
    assert c.can_undo()
    undone = c.undo()
    assert undone == Move.R
    assert c.is_solved()
    assert c.can_redo()


def test_redo_reapplies() -> None:
    c = CubeController()
    c.apply(Move.U)
    c.undo()
    redone = c.redo()
    assert redone == Move.U
    assert not c.is_solved()
    assert not c.can_redo()


def test_new_move_clears_redo() -> None:
    c = CubeController()
    c.apply(Move.U)
    c.undo()
    assert c.can_redo()
    c.apply(Move.R)  # fresh user move
    assert not c.can_redo()


def test_undo_empty_returns_none() -> None:
    c = CubeController()
    assert c.undo() is None


def test_redo_empty_returns_none() -> None:
    c = CubeController()
    assert c.redo() is None


def test_scramble_changes_state_and_resets_history() -> None:
    c = CubeController()
    scramble = c.scramble(20)
    assert len(scramble) == 20
    assert not c.is_solved()
    assert c.history == []
    assert c.move_count == 0


def test_reset_returns_to_solved() -> None:
    c = CubeController()
    c.scramble(20)
    c.apply(Move.R)
    c.reset()
    assert c.is_solved()
    assert not c.can_undo()
    assert c.move_count == 0


def test_undo_all_moves_restores_scrambled_base() -> None:
    c = CubeController()
    c.scramble(10)
    scrambled = c.state
    c.apply(Move.R)
    c.apply(Move.U)
    c.undo()
    c.undo()
    assert c.state == scrambled


def test_move_count_tracks_user_moves() -> None:
    c = CubeController()
    c.apply(Move.R)
    c.apply(Move.U)
    assert c.move_count == 2
    c.undo()
    assert c.move_count == 1
