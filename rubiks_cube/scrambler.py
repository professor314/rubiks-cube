"""Random scramble generator for the Rubik's cube.

Generates WCA-style scrambles where no two consecutive moves operate on
the same face.
"""

from __future__ import annotations

import random

from .moves import Move

_FACE_MOVES: dict[str, list[Move]] = {
    "U": [Move.U, Move.U_PRIME, Move.U2],
    "D": [Move.D, Move.D_PRIME, Move.D2],
    "L": [Move.L, Move.L_PRIME, Move.L2],
    "R": [Move.R, Move.R_PRIME, Move.R2],
    "F": [Move.F, Move.F_PRIME, Move.F2],
    "B": [Move.B, Move.B_PRIME, Move.B2],
}

_FACES = list(_FACE_MOVES.keys())


def generate_scramble(length: int = 20) -> list[Move]:
    """Generate a random scramble with no consecutive same-face moves.

    Parameters
    ----------
    length : int
        Number of moves (20-25 recommended for full scramble).

    Returns
    -------
    list[Move]
        Random move sequence.
    """
    moves: list[Move] = []
    last_face: str | None = None

    for _ in range(length):
        available = [f for f in _FACES if f != last_face]
        face = random.choice(available)
        moves.append(random.choice(_FACE_MOVES[face]))
        last_face = face

    return moves


def scramble_to_string(moves: list[Move]) -> str:
    """Convert a scramble to standard notation string.

    Parameters
    ----------
    moves : list[Move]
        The move sequence.

    Returns
    -------
    str
        Space-separated notation, e.g. "U R' F2 D L2".
    """
    return " ".join(m.value for m in moves)
