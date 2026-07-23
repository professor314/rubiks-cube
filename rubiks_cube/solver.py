"""Rubik's cube solver using Kociemba's two-phase algorithm.

Wraps the `kociemba` package. If not installed, raises ImportError
with installation instructions.
"""

from __future__ import annotations

from .cube_state import CubeState
from .moves import Move, parse_move_string
from .validation import is_valid_state


def solve(state: CubeState) -> list[Move]:
    """Find a near-optimal solution (≤20 moves) for the given cube state.

    Parameters
    ----------
    state : CubeState
        A valid, solvable cube configuration.

    Returns
    -------
    list[Move]
        Move sequence to solve the cube. Empty if already solved.

    Raises
    ------
    ImportError
        If kociemba is not installed.
    ValueError
        If the state is not valid/solvable.
    """
    if state.is_solved():
        return []

    if not is_valid_state(state):
        raise ValueError("Invalid cube state — not solvable.")

    try:
        import kociemba  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "kociemba not installed. Install with: pip install kociemba"
        ) from exc

    solution_str: str = kociemba.solve(state.to_kociemba_string())
    return parse_move_string(solution_str)
