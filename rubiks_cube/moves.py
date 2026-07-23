"""Rubik's cube move definitions and application.

Implements the 18 standard moves (6 faces x {CW, CCW, double}) and provides
functions to apply moves to a CubeState immutably.

Each move is defined by:
1. A clockwise rotation of the face itself (3x3 grid)
2. A 4-element cycle of edge strips on adjacent faces

The internal representation uses face index constants from cube_state:
    U=0, D=1, L=2, R=3, F=4, B=5

All moves are "clockwise when looking at the face from outside the cube."
"""

from __future__ import annotations

from enum import Enum

import numpy as np
from numpy.typing import NDArray

from .cube_state import B, CubeState, D, F, L, R, U


class Move(Enum):
    """Standard Rubik's cube moves (half-turn metric, 18 moves).

    Each move is named by the face it rotates:
    - Plain letter (e.g., U) = clockwise when looking at that face
    - Prime (e.g., U') = counter-clockwise
    - 2 (e.g., U2) = 180-degree turn
    """

    U = "U"
    U_PRIME = "U'"
    U2 = "U2"
    D = "D"
    D_PRIME = "D'"
    D2 = "D2"
    L = "L"
    L_PRIME = "L'"
    L2 = "L2"
    R = "R"
    R_PRIME = "R'"
    R2 = "R2"
    F = "F"
    F_PRIME = "F'"
    F2 = "F2"
    B = "B"
    B_PRIME = "B'"
    B2 = "B2"


def _rotate_face_cw(facelets: NDArray[np.int8], face: int) -> None:
    """Rotate a face 90° CW (looking from outside the cube) in-place.

    The numpy rotation direction depends on grid coordinate orientation:
    - U face: row 0 = back edge, so CW-from-above is np.rot90(k=1).
    - D, F, R, L, B faces: row 0 is the edge nearest the viewer when
      looking from outside, so CW-from-outside is np.rot90(k=-1).

    Parameters
    ----------
    facelets : NDArray[np.int8]
        The full (6, 3, 3) facelets array (mutable).
    face : int
        Index of the face to rotate (0-5).
    """
    if face == U:
        facelets[face] = np.rot90(facelets[face], k=1)
    else:
        facelets[face] = np.rot90(facelets[face], k=-1)


def _cycle4(
    facelets: NDArray[np.int8],
    positions: list[tuple[int, int, int]],
) -> None:
    """Perform a 4-element cyclic permutation: a->b->c->d->a.

    The value at positions[0] goes to positions[1], [1] to [2],
    [2] to [3], and [3] wraps to [0].

    Parameters
    ----------
    facelets : NDArray[np.int8]
        The full (6, 3, 3) facelets array (mutable).
    positions : list of (face, row, col) tuples
        Four positions to cycle.
    """
    temp = int(facelets[positions[3]])
    facelets[positions[3]] = facelets[positions[2]]
    facelets[positions[2]] = facelets[positions[1]]
    facelets[positions[1]] = facelets[positions[0]]
    facelets[positions[0]] = temp


def _apply_move_cw(facelets: NDArray[np.int8], face: int) -> None:
    """Apply a single CW face turn (face rotation + edge strip cycles).

    Parameters
    ----------
    facelets : NDArray[np.int8]
        The full (6, 3, 3) facelets array (mutable).
    face : int
        Which face to turn CW.
    """
    _rotate_face_cw(facelets, face)
    cycles = _EDGE_CYCLES[face]
    for cycle in cycles:
        _cycle4(facelets, cycle)



# Edge strip cycles for each face's CW rotation.
# Each face has 3 four-cycles representing the 12 stickers on adjacent faces.
# _cycle4([a, b, c, d]) rotates values: a->b->c->d->a
#
# For U and D, adjacent top/bottom rows cycle directly (no coordinate reversal).
# For R, L, F, B: the B face has reversed row indices because B is viewed from
# behind the cube (B[0,:] is top, but "left" from back = "right" from front).

_EDGE_CYCLES: dict[int, list[list[tuple[int, int, int]]]] = {
    # U face CW from above: F-top -> R-top -> B-top -> L-top
    U: [
        [(F, 0, 0), (R, 0, 0), (B, 0, 0), (L, 0, 0)],
        [(F, 0, 1), (R, 0, 1), (B, 0, 1), (L, 0, 1)],
        [(F, 0, 2), (R, 0, 2), (B, 0, 2), (L, 0, 2)],
    ],
    # D face CW from below: F-bottom -> R-bottom -> B-bottom -> L-bottom
    D: [
        [(F, 2, 0), (R, 2, 0), (B, 2, 0), (L, 2, 0)],
        [(F, 2, 1), (R, 2, 1), (B, 2, 1), (L, 2, 1)],
        [(F, 2, 2), (R, 2, 2), (B, 2, 2), (L, 2, 2)],
    ],
    # R face CW from right: F[:,2]->U[:,2]->B[:,0](rev)->D[:,2]
    R: [
        [(F, 0, 2), (U, 0, 2), (B, 2, 0), (D, 0, 2)],
        [(F, 1, 2), (U, 1, 2), (B, 1, 0), (D, 1, 2)],
        [(F, 2, 2), (U, 2, 2), (B, 0, 0), (D, 2, 2)],
    ],
    # L face CW from left: F[:,0]->D[:,0]->B[:,2](rev)->U[:,0]
    L: [
        [(F, 0, 0), (D, 0, 0), (B, 2, 2), (U, 0, 0)],
        [(F, 1, 0), (D, 1, 0), (B, 1, 2), (U, 1, 0)],
        [(F, 2, 0), (D, 2, 0), (B, 0, 2), (U, 2, 0)],
    ],
    # F face CW from front: U[2,:]->R[:,0]->D[0,:](rev)->L[:,2](rev)
    F: [
        [(U, 2, 0), (R, 0, 0), (D, 0, 2), (L, 2, 2)],
        [(U, 2, 1), (R, 1, 0), (D, 0, 1), (L, 1, 2)],
        [(U, 2, 2), (R, 2, 0), (D, 0, 0), (L, 0, 2)],
    ],
    # B face CW from back: U[0,:](rev)->L[:,0]->D[2,:](rev)->R[:,2]
    B: [
        [(U, 0, 2), (L, 0, 0), (D, 2, 0), (R, 2, 2)],
        [(U, 0, 1), (L, 1, 0), (D, 2, 1), (R, 1, 2)],
        [(U, 0, 0), (L, 2, 0), (D, 2, 2), (R, 0, 2)],
    ],
}



# Map Move enum to (face_index, rotation_count)
# rotation_count: 1=CW, 3=CCW (apply CW 3 times), 2=half-turn
_MOVE_TABLE: dict[Move, tuple[int, int]] = {
    Move.U: (U, 1),
    Move.U_PRIME: (U, 3),
    Move.U2: (U, 2),
    Move.D: (D, 1),
    Move.D_PRIME: (D, 3),
    Move.D2: (D, 2),
    Move.L: (L, 1),
    Move.L_PRIME: (L, 3),
    Move.L2: (L, 2),
    Move.R: (R, 1),
    Move.R_PRIME: (R, 3),
    Move.R2: (R, 2),
    Move.F: (F, 1),
    Move.F_PRIME: (F, 3),
    Move.F2: (F, 2),
    Move.B: (B, 1),
    Move.B_PRIME: (B, 3),
    Move.B2: (B, 2),
}


def apply_move(state: CubeState, move: Move) -> CubeState:
    """Apply a single move to produce a new CubeState (immutable).

    Parameters
    ----------
    state : CubeState
        The current cube state.
    move : Move
        The move to apply.

    Returns
    -------
    CubeState
        A new CubeState with the move applied.

    Examples
    --------
    >>> cube = CubeState.solved()
    >>> moved = apply_move(cube, Move.U)
    >>> moved.is_solved()
    False
    """
    face_idx, count = _MOVE_TABLE[move]
    facelets = state.facelets.copy()
    facelets.flags.writeable = True
    for _ in range(count):
        _apply_move_cw(facelets, face_idx)
    return CubeState(facelets=facelets)


def apply_sequence(state: CubeState, moves: list[Move]) -> CubeState:
    """Apply a sequence of moves to produce a new CubeState.

    Parameters
    ----------
    state : CubeState
        The initial cube state.
    moves : list[Move]
        The sequence of moves to apply in order.

    Returns
    -------
    CubeState
        The resulting state after all moves.

    Examples
    --------
    >>> cube = CubeState.solved()
    >>> result = apply_sequence(cube, [Move.U, Move.U_PRIME])
    >>> result.is_solved()
    True
    """
    for move in moves:
        state = apply_move(state, move)
    return state


# Inverse move mapping
_INVERSE_MAP: dict[Move, Move] = {
    Move.U: Move.U_PRIME,
    Move.U_PRIME: Move.U,
    Move.U2: Move.U2,
    Move.D: Move.D_PRIME,
    Move.D_PRIME: Move.D,
    Move.D2: Move.D2,
    Move.L: Move.L_PRIME,
    Move.L_PRIME: Move.L,
    Move.L2: Move.L2,
    Move.R: Move.R_PRIME,
    Move.R_PRIME: Move.R,
    Move.R2: Move.R2,
    Move.F: Move.F_PRIME,
    Move.F_PRIME: Move.F,
    Move.F2: Move.F2,
    Move.B: Move.B_PRIME,
    Move.B_PRIME: Move.B,
    Move.B2: Move.B2,
}


def inverse_move(move: Move) -> Move:
    """Return the inverse of a move.

    U -> U', U' -> U, U2 -> U2 (self-inverse).

    Parameters
    ----------
    move : Move
        The move to invert.

    Returns
    -------
    Move
        The inverse move.

    Examples
    --------
    >>> inverse_move(Move.U)
    <Move.U_PRIME: "U'">
    >>> inverse_move(Move.U2)
    <Move.U2: 'U2'>
    """
    return _INVERSE_MAP[move]


def inverse_sequence(moves: list[Move]) -> list[Move]:
    """Reverse and invert a move sequence.

    The inverse of a sequence is the reversed sequence with each move inverted.

    Parameters
    ----------
    moves : list[Move]
        The move sequence to invert.

    Returns
    -------
    list[Move]
        The inverse sequence.

    Examples
    --------
    >>> inverse_sequence([Move.U, Move.R, Move.F])
    [<Move.F_PRIME: "F'">, <Move.R_PRIME: "R'">, <Move.U_PRIME: "U'">]
    """
    return [inverse_move(m) for m in reversed(moves)]


def move_to_string(moves: list[Move]) -> str:
    """Convert a list of Moves to a space-separated notation string.

    Parameters
    ----------
    moves : list[Move]
        The move list to convert.

    Returns
    -------
    str
        Space-separated move notation string.

    Examples
    --------
    >>> move_to_string([Move.U, Move.R_PRIME, Move.F2])
    "U R' F2"
    """
    return " ".join(m.value for m in moves)


# Parsing notation string to Move list
_NOTATION_MAP: dict[str, Move] = {
    "U": Move.U,
    "U'": Move.U_PRIME,
    "U2": Move.U2,
    "D": Move.D,
    "D'": Move.D_PRIME,
    "D2": Move.D2,
    "L": Move.L,
    "L'": Move.L_PRIME,
    "L2": Move.L2,
    "R": Move.R,
    "R'": Move.R_PRIME,
    "R2": Move.R2,
    "F": Move.F,
    "F'": Move.F_PRIME,
    "F2": Move.F2,
    "B": Move.B,
    "B'": Move.B_PRIME,
    "B2": Move.B2,
}


def parse_move_string(s: str) -> list[Move]:
    """Parse a space-separated move notation string into a list of Moves.

    Parameters
    ----------
    s : str
        Space-separated move notation, e.g. "U R' F2 D".

    Returns
    -------
    list[Move]
        The parsed move list.

    Raises
    ------
    ValueError
        If an unrecognized move token is encountered.

    Examples
    --------
    >>> parse_move_string("U R' F2")
    [<Move.U: 'U'>, <Move.R_PRIME: "R'">, <Move.F2: 'F2'>]
    """
    if not s.strip():
        return []
    moves: list[Move] = []
    for token in s.strip().split():
        if token not in _NOTATION_MAP:
            raise ValueError(f"Unrecognized move notation: '{token}'")
        moves.append(_NOTATION_MAP[token])
    return moves
