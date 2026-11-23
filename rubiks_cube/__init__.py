"""Rubik's cube: state, moves, scrambler, solver, timer, stats, viz, validation.

Public names are exposed lazily (PEP 562) so that importing a lightweight,
dependency-free submodule such as :mod:`rubiks_cube.stats` does not pull in
numpy/matplotlib. The heavy engine and visualization modules are only imported
on first access of their names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Map public attribute name -> (submodule, attribute in that submodule)
_LAZY: dict[str, tuple[str, str]] = {
    "CubeState": ("cube_state", "CubeState"),
    "CubeTimer": ("timer", "CubeTimer"),
    "Move": ("moves", "Move"),
    "apply_move": ("moves", "apply_move"),
    "apply_sequence": ("moves", "apply_sequence"),
    "inverse_move": ("moves", "inverse_move"),
    "inverse_sequence": ("moves", "inverse_sequence"),
    "move_to_string": ("moves", "move_to_string"),
    "parse_move_string": ("moves", "parse_move_string"),
    "generate_scramble": ("scrambler", "generate_scramble"),
    "scramble_to_string": ("scrambler", "scramble_to_string"),
    "is_valid_state": ("validation", "is_valid_state"),
    "solve": ("solver", "solve"),
    "run_rubiks_cube": ("cube_viz", "run_rubiks_cube"),
    # Pure-Python stats (no heavy deps)
    "Solve": ("stats", "Solve"),
    "SolveStats": ("stats", "SolveStats"),
    "SessionStore": ("session", "SessionStore"),
    "scramble_of_the_day": ("session", "scramble_of_the_day"),
}

if TYPE_CHECKING:  # pragma: no cover - for static analysis only
    # Re-exported lazily at runtime via __getattr__; imported here only so
    # static analyzers and IDEs can resolve the public names.
    from .cube_state import CubeState as CubeState
    from .moves import Move as Move
    from .moves import apply_move as apply_move
    from .moves import apply_sequence as apply_sequence
    from .moves import inverse_move as inverse_move
    from .moves import inverse_sequence as inverse_sequence
    from .moves import move_to_string as move_to_string
    from .moves import parse_move_string as parse_move_string
    from .scrambler import generate_scramble as generate_scramble
    from .scrambler import scramble_to_string as scramble_to_string
    from .session import SessionStore as SessionStore
    from .session import scramble_of_the_day as scramble_of_the_day
    from .solver import solve as solve
    from .stats import Solve as Solve
    from .stats import SolveStats as SolveStats
    from .timer import CubeTimer as CubeTimer
    from .validation import is_valid_state as is_valid_state


def __getattr__(name: str) -> Any:
    """Lazily import and return a public attribute (PEP 562)."""
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = target
    import importlib

    module = importlib.import_module(f".{module_name}", __name__)
    value = getattr(module, attr)
    globals()[name] = value  # cache for subsequent access
    return value


def __dir__() -> list[str]:
    return sorted(_LAZY)


__all__ = [
    "CubeState",
    "CubeTimer",
    "Move",
    "SessionStore",
    "Solve",
    "SolveStats",
    "apply_move",
    "apply_sequence",
    "generate_scramble",
    "inverse_move",
    "inverse_sequence",
    "is_valid_state",
    "move_to_string",
    "parse_move_string",
    "run_rubiks_cube",
    "scramble_of_the_day",
    "scramble_to_string",
    "solve",
]
