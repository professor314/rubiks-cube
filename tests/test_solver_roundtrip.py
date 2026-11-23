"""Regression tests: the solver's moves must actually solve the cube.

An earlier bug made the U move turn the wrong way, so the solver printed a
move list that left the cube scrambled. These tests catch that kind of mismatch
between the engine's move definitions and the Kociemba solver's conventions.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("kociemba")

import kociemba

from rubiks_cube.controller import CubeController
from rubiks_cube.cube_state import CubeState
from rubiks_cube.moves import Move, apply_move, inverse_move

_QUARTER_TURNS = [m for m in Move if not m.value.endswith("2")]


@pytest.mark.parametrize("move", _QUARTER_TURNS, ids=lambda m: m.value)
def test_single_move_is_undone_by_the_solver(move: Move) -> None:
    """The solver must answer a single move with that move's inverse."""
    state = apply_move(CubeState.solved(), move)
    solution = kociemba.solve(state.to_kociemba_string())
    assert solution.split() == [inverse_move(move).value]


def test_solution_solves_random_scrambles() -> None:
    """Applying the solver's output to a scrambled cube must solve it."""
    for _ in range(25):
        controller = CubeController()
        controller.scramble(25)
        controller.apply_solution(controller.solve())
        assert controller.is_solved()
