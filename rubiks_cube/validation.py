"""Rubik's cube state validation.

Validates whether a given cube state is solvable by checking:
1. Correct facelet count (exactly 9 of each color)
2. Valid edge orientations (sum of edge orientations is 0 mod 2)
3. Valid corner orientations (sum of corner orientations is 0 mod 3)
4. Valid permutation parity (edge and corner permutation parities match)
"""

from __future__ import annotations

import numpy as np

from .cube_state import B, CubeState, D, F, L, R, U

# Corner cubies: defined by the three facelets they show.
# Each tuple is (face1, row1, col1, face2, row2, col2, face3, row3, col3)
# ordered so that the U/D facelet comes first (defines orientation reference).
#
# Corner positions (8 corners):
# URF, UFL, ULB, UBR, DFR, DLF, DBL, DRB
_CORNERS: list[tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = [
    # URF: U[2,2], R[0,0], F[0,2]
    ((U, 2, 2), (R, 0, 0), (F, 0, 2)),
    # UFL: U[2,0], F[0,0], L[0,2]
    ((U, 2, 0), (F, 0, 0), (L, 0, 2)),
    # ULB: U[0,0], L[0,0], B[0,2]
    ((U, 0, 0), (L, 0, 0), (B, 0, 2)),
    # UBR: U[0,2], B[0,0], R[0,2]
    ((U, 0, 2), (B, 0, 0), (R, 0, 2)),
    # DFR: D[0,2], F[2,2], R[2,0]
    ((D, 0, 2), (F, 2, 2), (R, 2, 0)),
    # DLF: D[0,0], L[2,2], F[2,0]
    ((D, 0, 0), (L, 2, 2), (F, 2, 0)),
    # DBL: D[2,0], B[2,2], L[2,0]
    ((D, 2, 0), (B, 2, 2), (L, 2, 0)),
    # DRB: D[2,2], R[2,2], B[2,0]
    ((D, 2, 2), (R, 2, 2), (B, 2, 0)),
]

# Edge cubies: defined by their two facelets.
# Each tuple is (face1, row1, col1, face2, row2, col2)
# First facelet is the "reference" for orientation (U/D face, or F/B face if no U/D).
#
# Edge positions (12 edges):
# UF, UL, UB, UR, DF, DL, DB, DR, FR, FL, BL, BR
_EDGES: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    # UF: U[2,1], F[0,1]
    ((U, 2, 1), (F, 0, 1)),
    # UL: U[1,0], L[0,1]
    ((U, 1, 0), (L, 0, 1)),
    # UB: U[0,1], B[0,1]
    ((U, 0, 1), (B, 0, 1)),
    # UR: U[1,2], R[0,1]
    ((U, 1, 2), (R, 0, 1)),
    # DF: D[0,1], F[2,1]
    ((D, 0, 1), (F, 2, 1)),
    # DL: D[1,0], L[2,1]
    ((D, 1, 0), (L, 2, 1)),
    # DB: D[2,1], B[2,1]
    ((D, 2, 1), (B, 2, 1)),
    # DR: D[1,2], R[2,1]
    ((D, 1, 2), (R, 2, 1)),
    # FR: F[1,2], R[1,0]
    ((F, 1, 2), (R, 1, 0)),
    # FL: F[1,0], L[1,2]
    ((F, 1, 0), (L, 1, 2)),
    # BL: B[1,2], L[1,0]
    ((B, 1, 2), (L, 1, 0)),
    # BR: B[1,0], R[1,2]
    ((B, 1, 0), (R, 1, 2)),
]

# The solved color for each corner position (U/D color, then two side colors CW)
_CORNER_COLORS: list[tuple[int, int, int]] = [
    (U, R, F),  # URF
    (U, F, L),  # UFL
    (U, L, B),  # ULB
    (U, B, R),  # UBR
    (D, F, R),  # DFR
    (D, L, F),  # DLF
    (D, B, L),  # DBL
    (D, R, B),  # DRB
]

# The solved color for each edge position (reference color, then other)
_EDGE_COLORS: list[tuple[int, int]] = [
    (U, F),  # UF
    (U, L),  # UL
    (U, B),  # UB
    (U, R),  # UR
    (D, F),  # DF
    (D, L),  # DL
    (D, B),  # DB
    (D, R),  # DR
    (F, R),  # FR
    (F, L),  # FL
    (B, L),  # BL
    (B, R),  # BR
]


def _get_facelet(state: CubeState, pos: tuple[int, int, int]) -> int:
    """Get the color of a facelet at (face, row, col)."""
    return int(state.facelets[pos[0], pos[1], pos[2]])


def _identify_corner(colors: tuple[int, int, int]) -> int | None:
    """Identify which corner cubie has these three colors. Returns index or None."""
    color_set = set(colors)
    for i, ref_colors in enumerate(_CORNER_COLORS):
        if set(ref_colors) == color_set:
            return i
    return None


def _corner_orientation(
    actual_colors: tuple[int, int, int], corner_idx: int
) -> int | None:
    """Determine orientation of a corner (0, 1, or 2 twists CW).

    Orientation 0: the U/D color is in the U/D position.
    Orientation 1: the U/D color is one twist CW away.
    Orientation 2: the U/D color is two twists CW away.
    """
    ref = _CORNER_COLORS[corner_idx]
    # The reference U/D color for this corner
    ud_color = ref[0]

    if actual_colors[0] == ud_color:
        return 0
    elif actual_colors[1] == ud_color:
        return 1
    elif actual_colors[2] == ud_color:
        return 2
    return None


def _identify_edge(colors: tuple[int, int]) -> int | None:
    """Identify which edge cubie has these two colors. Returns index or None."""
    color_set = set(colors)
    for i, ref_colors in enumerate(_EDGE_COLORS):
        if set(ref_colors) == color_set:
            return i
    return None


def _edge_orientation(actual_colors: tuple[int, int], edge_idx: int) -> int | None:
    """Determine orientation of an edge (0 = correct, 1 = flipped).

    Orientation 0: the reference color is in the reference position.
    Orientation 1: the reference color is in the other position.
    """
    ref = _EDGE_COLORS[edge_idx]
    ref_color = ref[0]  # The "reference" color (U/D, or F/B if no U/D)

    if actual_colors[0] == ref_color:
        return 0
    elif actual_colors[1] == ref_color:
        return 1
    return None


def _parity(perm: list[int]) -> int:
    """Calculate the parity of a permutation (0 = even, 1 = odd)."""
    n = len(perm)
    visited = [False] * n
    parity = 0
    for i in range(n):
        if not visited[i]:
            cycle_len = 0
            j = i
            while not visited[j]:
                visited[j] = True
                j = perm[j]
                cycle_len += 1
            parity += (cycle_len - 1) % 2
    return parity % 2


def is_valid_state(state: CubeState) -> bool:
    """Check whether a cube state is solvable.

    Validates:
    1. Exactly 9 facelets of each color (0-5)
    2. All 8 corners are identifiable and have valid orientations summing to 0 mod 3
    3. All 12 edges are identifiable and have valid orientations summing to 0 mod 2
    4. Corner and edge permutation parities are equal (both even or both odd)

    Parameters
    ----------
    state : CubeState
        The cube state to validate.

    Returns
    -------
    bool
        True if the state represents a solvable cube configuration.

    Examples
    --------
    >>> is_valid_state(CubeState.solved())
    True
    """
    facelets = state.facelets

    # Check 1: Exactly 9 facelets of each color
    for color in range(6):
        count = np.sum(facelets == color)
        if count != 9:
            return False

    # Check 2: Identify corners and compute orientations
    corner_perm: list[int] = []
    corner_orient_sum = 0
    for i, (pos1, pos2, pos3) in enumerate(_CORNERS):
        c1 = _get_facelet(state, pos1)
        c2 = _get_facelet(state, pos2)
        c3 = _get_facelet(state, pos3)
        colors = (c1, c2, c3)

        corner_idx = _identify_corner(colors)
        if corner_idx is None:
            return False

        orient = _corner_orientation(colors, corner_idx)
        if orient is None:
            return False

        corner_perm.append(corner_idx)
        corner_orient_sum += orient

    # Corner orientation sum must be 0 mod 3
    if corner_orient_sum % 3 != 0:
        return False

    # Check for duplicates in corner permutation
    if len(set(corner_perm)) != 8:
        return False

    # Check 3: Identify edges and compute orientations
    edge_perm: list[int] = []
    edge_orient_sum = 0
    for i, (pos1, pos2) in enumerate(_EDGES):
        c1 = _get_facelet(state, pos1)
        c2 = _get_facelet(state, pos2)
        colors = (c1, c2)

        edge_idx = _identify_edge(colors)
        if edge_idx is None:
            return False

        orient = _edge_orientation(colors, edge_idx)
        if orient is None:
            return False

        edge_perm.append(edge_idx)
        edge_orient_sum += orient

    # Edge orientation sum must be 0 mod 2
    if edge_orient_sum % 2 != 0:
        return False

    # Check for duplicates in edge permutation
    if len(set(edge_perm)) != 12:
        return False

    # Check 4: Permutation parities must match
    corner_par = _parity(corner_perm)
    edge_par = _parity(edge_perm)
    if corner_par != edge_par:
        return False

    return True
