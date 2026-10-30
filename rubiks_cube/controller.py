"""Application controller: cube state + move history + undo/redo.

This holds all the *non-GUI* interaction logic so it can be unit-tested without
matplotlib. The engine (numpy-backed) is imported lazily, so simply importing
this module is dependency-free; constructing a :class:`CubeController` requires
the engine.

The controller tracks a move history and supports undo/redo, scrambling,
resetting, and (optionally) solving via the engine's solver.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .cube_state import CubeState
    from .moves import Move


class CubeController:
    """Owns the cube state and an undo/redo history of applied moves.

    Notes
    -----
    - ``history`` is the list of moves applied from the current *base* state
      (the state at the last scramble/reset).
    - ``redo_stack`` holds moves undone but not yet re-applied; it is cleared
      whenever a brand-new move is made.
    """

    def __init__(self) -> None:
        from .cube_state import CubeState

        self._base: CubeState = CubeState.solved()
        self._state: CubeState = self._base
        self.history: list[Move] = []
        self.redo_stack: list[Move] = []
        self.move_count: int = 0

    @property
    def state(self) -> CubeState:
        """Current cube state."""
        return self._state

    def is_solved(self) -> bool:
        """Whether the cube is currently solved."""
        return self._state.is_solved()

    def apply(self, move: Move, *, user_move: bool = True) -> None:
        """Apply a single move, pushing it onto the history.

        Parameters
        ----------
        move : Move
            The move to apply.
        user_move : bool
            If True, this is a fresh user action and the redo stack is cleared.
        """
        from .moves import apply_move

        self._state = apply_move(self._state, move)
        self.history.append(move)
        if user_move:
            self.redo_stack.clear()
        self.move_count += 1

    def can_undo(self) -> bool:
        """Whether there is a move available to undo."""
        return len(self.history) > 0

    def can_redo(self) -> bool:
        """Whether there is a move available to redo."""
        return len(self.redo_stack) > 0

    def undo(self) -> Move | None:
        """Undo the last move. Returns the undone move, or None if nothing to undo."""
        if not self.history:
            return None
        from .moves import apply_move, inverse_move

        move = self.history.pop()
        self._state = apply_move(self._state, inverse_move(move))
        self.redo_stack.append(move)
        self.move_count = max(0, self.move_count - 1)
        return move

    def redo(self) -> Move | None:
        """Redo the last undone move. Returns it, or None if nothing to redo."""
        if not self.redo_stack:
            return None
        move = self.redo_stack.pop()
        self.apply(move, user_move=False)
        return move

    def scramble(self, length: int = 20) -> list[Move]:
        """Scramble the cube from solved and reset history. Returns the scramble."""
        from .cube_state import CubeState
        from .moves import apply_sequence
        from .scrambler import generate_scramble

        scramble = generate_scramble(length)
        self._base = CubeState.solved()
        self._state = apply_sequence(self._base, scramble)
        self.history.clear()
        self.redo_stack.clear()
        self.move_count = 0
        return scramble

    def reset(self) -> None:
        """Reset to a solved cube and clear all history."""
        from .cube_state import CubeState

        self._base = CubeState.solved()
        self._state = self._base
        self.history.clear()
        self.redo_stack.clear()
        self.move_count = 0

    def solve(self) -> list[Move]:
        """Compute a solution for the current state (requires the solver).

        Returns
        -------
        list[Move]
            The solution move sequence (empty if already solved).

        Raises
        ------
        ImportError
            If the optional ``kociemba`` solver is not installed.
        """
        from .solver import solve as _solve

        return _solve(self._state)

    def apply_solution(self, solution: list[Move]) -> None:
        """Apply a solution sequence to the cube, recording it in history."""
        for move in solution:
            self.apply(move, user_move=False)
