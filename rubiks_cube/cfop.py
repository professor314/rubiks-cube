"""CFOP ("Fridrich") solver: cross, F2L, 2-look OLL, 2-look PLL.

This is the method most speedcubers use, so the solutions it produces are long
(roughly 50 to 70 moves) but follow the steps a human would take. For the
shortest possible solution use :mod:`rubiks_cube.solver` (Kociemba) instead.

The cross goes on the bottom (D) face. Steps:

1. **Cross**: place the four D-face edges (found optimally, at most 8 moves).
2. **F2L** (first two layers): insert the four corner+edge pairs one at a
   time. The pair that needs the fewest moves is solved first. Each pair is
   found by an IDA* search that keeps the cross and every earlier pair intact.
3. **OLL**, two looks: orient the top edges, then the top corners, using the
   standard speedcubing algorithms.
4. **PLL**, two looks: permute the top corners, then the top edges (with a final
   U turn to line everything up).

The OLL/PLL steps try short sequences of known algorithms (with U turns in
between) and keep the shortest one that works, so every step is verified
against the real cube state, not assumed.

Pieces are tracked as *sticker positions* (indices 0 to 53 in the engine's
``(6, 3, 3)`` array, ``face * 9 + row * 3 + col``). A move is then a byte
translation table, which makes the searches fast enough for pure Python.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from functools import cache, lru_cache
from typing import TYPE_CHECKING, Any

from .cube_state import CubeState
from .moves import Move, apply_move, apply_sequence, parse_move_string
from .validation import is_valid_state

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

    from numpy.typing import NDArray

_U, _D, _L, _R, _F, _B = range(6)


def _ix(face: int, row: int, col: int) -> int:
    """Index of a facelet in the flattened 54-sticker array."""
    return face * 9 + row * 3 + col


# Sticker indices of every edge / corner in its SOLVED position. The colour of
# a sticker in the solved cube is simply its face index (index // 9).
_EDGES: dict[str, tuple[int, ...]] = {
    "UF": (_ix(_U, 2, 1), _ix(_F, 0, 1)),
    "UR": (_ix(_U, 1, 2), _ix(_R, 0, 1)),
    "UB": (_ix(_U, 0, 1), _ix(_B, 0, 1)),
    "UL": (_ix(_U, 1, 0), _ix(_L, 0, 1)),
    "DF": (_ix(_D, 0, 1), _ix(_F, 2, 1)),
    "DR": (_ix(_D, 1, 2), _ix(_R, 2, 1)),
    "DB": (_ix(_D, 2, 1), _ix(_B, 2, 1)),
    "DL": (_ix(_D, 1, 0), _ix(_L, 2, 1)),
    "FR": (_ix(_F, 1, 2), _ix(_R, 1, 0)),
    "FL": (_ix(_F, 1, 0), _ix(_L, 1, 2)),
    "BR": (_ix(_B, 1, 0), _ix(_R, 1, 2)),
    "BL": (_ix(_B, 1, 2), _ix(_L, 1, 0)),
}
_CORNERS: dict[str, tuple[int, ...]] = {
    "URF": (_ix(_U, 2, 2), _ix(_R, 0, 0), _ix(_F, 0, 2)),
    "UFL": (_ix(_U, 2, 0), _ix(_F, 0, 0), _ix(_L, 0, 2)),
    "ULB": (_ix(_U, 0, 0), _ix(_L, 0, 0), _ix(_B, 0, 2)),
    "UBR": (_ix(_U, 0, 2), _ix(_B, 0, 0), _ix(_R, 0, 2)),
    "DFR": (_ix(_D, 0, 2), _ix(_F, 2, 2), _ix(_R, 2, 0)),
    "DLF": (_ix(_D, 0, 0), _ix(_L, 2, 2), _ix(_F, 2, 0)),
    "DBL": (_ix(_D, 2, 0), _ix(_B, 2, 2), _ix(_L, 2, 0)),
    "DRB": (_ix(_D, 2, 2), _ix(_R, 2, 2), _ix(_B, 2, 0)),
}
_PIECES: dict[str, tuple[int, ...]] = {**_EDGES, **_CORNERS}

_CROSS_EDGES = ("DF", "DR", "DB", "DL")
# F2L slot -> (corner, edge, faces that turn it in/out of the slot).
_F2L_SLOTS: dict[str, tuple[str, str, str]] = {
    "DFR": ("DFR", "FR", "RF"),
    "DLF": ("DLF", "FL", "LF"),
    "DBL": ("DBL", "BL", "LB"),
    "DRB": ("DRB", "BR", "RB"),
}
_TOP_CORNERS = ("URF", "UFL", "ULB", "UBR")
_TOP_EDGE_STICKERS = (_ix(_U, 0, 1), _ix(_U, 1, 0), _ix(_U, 1, 2), _ix(_U, 2, 1))

_OPPOSITE = {"U": "D", "D": "U", "L": "R", "R": "L", "F": "B", "B": "F"}


@dataclass(frozen=True)
class Stage:
    """One labelled step of a solution (for example ``"CROSS"``)."""

    name: str
    moves: tuple[Move, ...]


# --------------------------------------------------------------------------
# Move tables
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _move_tables() -> dict[Move, bytes]:
    """For each move, a 256-byte table sending a sticker index to where it goes.

    ``bytes.translate`` with this table moves every tracked sticker at once.
    """
    import numpy as np

    base = CubeState(np.arange(54, dtype=np.int8).reshape(6, 3, 3))
    tables: dict[Move, bytes] = {}
    for mv in Move:
        after = apply_move(base, mv).facelets.reshape(54)
        dest = list(range(256))
        for new_pos in range(54):
            dest[int(after[new_pos])] = new_pos
        tables[mv] = bytes(dest)
    return tables


def _bfs(goal: bytes, tables: Sequence[bytes]) -> dict[bytes, int]:
    """Distance (in moves) from every reachable tracked state to ``goal``."""
    dist = {goal: 0}
    frontier = [goal]
    depth = 0
    while frontier:
        depth += 1
        nxt: list[bytes] = []
        for state in frontier:
            for table in tables:
                new = state.translate(table)
                if new not in dist:
                    dist[new] = depth
                    nxt.append(new)
        frontier = nxt
    return dist


# --------------------------------------------------------------------------
# Locating pieces
# --------------------------------------------------------------------------
def _locate(cur: Sequence[int], piece: str) -> bytes:
    """Current sticker positions of ``piece`` (same order as its solved stickers)."""
    solved = _PIECES[piece]
    colours = [i // 9 for i in solved]
    slots = _EDGES if piece in _EDGES else _CORNERS
    for slot in slots.values():
        if sorted(cur[i] for i in slot) == sorted(colours):
            return bytes(next(i for i in slot if cur[i] == c) for c in colours)
    raise ValueError(f"piece {piece} not found: invalid cube state")


def _tracked(cur: Sequence[int], pieces: Sequence[str]) -> bytes:
    return b"".join(_locate(cur, p) for p in pieces)


def _goal(pieces: Sequence[str]) -> bytes:
    return bytes(i for p in pieces for i in _PIECES[p])


def _cur_list(state: CubeState) -> list[int]:
    return [int(v) for v in state.facelets.reshape(54)]


# --------------------------------------------------------------------------
# Move-sequence helpers
# --------------------------------------------------------------------------
def _face(move: Move) -> str:
    return move.value[0]


def _quarter(move: Move) -> int:
    if move.value.endswith("2"):
        return 2
    return 3 if move.value.endswith("'") else 1


def _merge(moves: Sequence[Move]) -> list[Move]:
    """Combine consecutive turns of the same face (R R -> R2, R R' -> nothing)."""
    stack: list[tuple[str, int]] = []
    for mv in moves:
        face, quarter = _face(mv), _quarter(mv)
        if stack and stack[-1][0] == face:
            quarter = (stack.pop()[1] + quarter) % 4
        if quarter:
            stack.append((face, quarter))
    suffix = {1: "", 2: "2", 3: "'"}
    return [Move(f"{face}{suffix[q]}") for face, q in stack]


def _apply(state: CubeState, moves: Sequence[Move]) -> CubeState:
    return apply_sequence(state, list(moves))


# --------------------------------------------------------------------------
# Stage 1: cross
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _cross_table() -> dict[bytes, int]:
    """Distance table for the four cross edges (about 190,000 states)."""
    return _bfs(_goal(_CROSS_EDGES), list(_move_tables().values()))


def warm_up() -> None:
    """Build the lookup tables now (takes a few seconds) so the first solve is fast."""
    _cross_table()
    for slot in _F2L_SLOTS:
        _pair_table(slot)


def _solve_cross(state: CubeState) -> list[Move]:
    table = _cross_table()
    tables = _move_tables()
    cur = _tracked(_cur_list(state), _CROSS_EDGES)
    path: list[Move] = []
    while table[cur] > 0:
        want = table[cur] - 1
        for mv, tbl in tables.items():
            nxt = cur.translate(tbl)
            if table.get(nxt) == want:
                path.append(mv)
                cur = nxt
                break
    return path


# --------------------------------------------------------------------------
# Stage 2: F2L
# --------------------------------------------------------------------------
@cache
def _pair_table(slot: str) -> dict[bytes, int]:
    """Distance table for one corner+edge pair on its own (a lower bound)."""
    corner, edge, _ = _F2L_SLOTS[slot]
    return _bfs(_goal([corner, edge]), list(_move_tables().values()))


def _moves_for(faces: str) -> list[tuple[Move, bytes, str]]:
    tables = _move_tables()
    return [(mv, tables[mv], _face(mv)) for mv in Move if _face(mv) in faces]


def _pair_search(
    start: bytes,
    goal: bytes,
    heuristic: dict[bytes, int],
    moves: list[tuple[Move, bytes, str]],
    limit: int,
) -> list[Move] | None:
    """IDA* step: find <= ``limit`` moves taking ``start`` to ``goal``."""
    path: list[Move] = []

    def rec(state: bytes, depth: int, last: str) -> bool:
        if state == goal:
            return True
        if depth + heuristic[state[-5:]] > limit:
            return False
        for mv, table, face in moves:
            if face == last or (_OPPOSITE[face] == last and face > last):
                continue
            path.append(mv)
            if rec(state.translate(table), depth + 1, face):
                return True
            path.pop()
        return False

    return list(path) if rec(start, 0, "") else None


# Move sets tried in order: U plus the two faces touching the slot (the natural
# F2L moves), then everything except D, which would break the cross.
_F2L_TIERS = (("slot", 9), ("no-D", 10))


def _solve_f2l(state: CubeState) -> list[Stage]:
    remaining = list(_F2L_SLOTS)
    solved_pieces: list[str] = list(_CROSS_EDGES)
    stages: list[Stage] = []
    count = 0
    while remaining:
        cur = _cur_list(state)
        found: tuple[str, list[Move]] | None = None
        for tier, max_limit in _F2L_TIERS:
            for limit in range(max_limit + 1):
                for slot in remaining:
                    corner, edge, slot_faces = _F2L_SLOTS[slot]
                    pieces = [*solved_pieces, corner, edge]
                    faces = "U" + slot_faces if tier == "slot" else "URFLB"
                    result = _pair_search(
                        _tracked(cur, pieces),
                        _goal(pieces),
                        _pair_table(slot),
                        _moves_for(faces),
                        limit,
                    )
                    if result is not None:
                        found = (slot, result)
                        break
                if found:
                    break
            if found:
                break
        if found is None:
            raise ValueError("CFOP: could not solve an F2L pair")
        slot, moves = found
        count += 1
        corner, edge, _ = _F2L_SLOTS[slot]
        solved_pieces += [corner, edge]
        remaining.remove(slot)
        state = _apply(state, moves)
        if moves:
            stages.append(Stage(f"F2L {count}/4 ({slot})", tuple(_merge(moves))))
    return stages


# --------------------------------------------------------------------------
# Stages 3 and 4: 2-look OLL and PLL
# --------------------------------------------------------------------------
def _alg(text: str) -> list[Move]:
    return parse_move_string(text)


# Algorithms are written for a cube held with the cross on D. Each stage tries
# U turns before/between them, so one alg covers all four rotations of a case.
_OLL_EDGE_ALGS = {
    "line": "F R U R' U' F'",
    "L-shape": "F U R U' R' F'",
}
_OLL_CORNER_ALGS = {
    "Sune": "R U R' U R U2 R'",
    "Anti-Sune": "R U2 R' U' R U' R'",
    "H": "F R U R' U' R U R' U' R U R' U' F'",
    "Pi": "R U2 R2 U' R2 U' R2 U2 R",
    "U": "R2 D R' U2 R D' R' U2 R'",
    "T": "L F R' F' L' F R F'",
    "L": "R' F R B' R' F' R B",
}
_PLL_CORNER_ALGS = {
    "Y-perm": "F R U' R' U' R U R' F' R U R' U' R' F R F'",
    "T-perm": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "Ja-perm": "R' U L' U2 R U' R' U2 R L",
}
_PLL_EDGE_ALGS = {
    "Ua-perm": "R U' R U R U R U' R' U' R2",
    "Ub-perm": "R2 U R U R' U' R' U' R' U R'",
    "H-perm": "R2 U2 R U2 R2 U2 R2 U2 R U2 R2",
    "Jb-perm": "R U R' F' R U R' U' R' F R2 U' R'",
}
_AUFS = ("", "U", "U'", "U2")


def _perm(moves: Sequence[Move]) -> NDArray[Any]:
    """Permutation array: ``new_colours = old_colours[perm]``."""
    import numpy as np

    base = CubeState(np.arange(54, dtype=np.int8).reshape(6, 3, 3))
    return _apply(base, moves).facelets.reshape(54).astype(np.int64)


def _solved_colours() -> NDArray[Any]:
    import numpy as np

    return np.repeat(np.arange(6), 9)


def _edges_oriented(cur: NDArray[Any]) -> bool:
    return bool((cur[list(_TOP_EDGE_STICKERS)] == 0).all())


def _top_oriented(cur: NDArray[Any]) -> bool:
    return bool((cur[:9] == 0).all())


def _corners_placed(cur: NDArray[Any]) -> bool:
    return all(cur[i] == i // 9 for c in _TOP_CORNERS for i in _CORNERS[c])


def _all_solved(cur: NDArray[Any]) -> bool:
    return bool((cur == _solved_colours()).all())


def _look_search(
    state: CubeState,
    algs: dict[str, str],
    goal: Any,
    max_looks: int,
    final_auf: bool,
) -> list[Move]:
    """Shortest sequence of (U turn + alg) "looks" that satisfies ``goal``.

    Tries 1 look, then 2, up to ``max_looks``; among sequences with the fewest
    looks it keeps the one with the fewest moves after merging.
    """
    import numpy as np

    cur0 = np.array(_cur_list(state), dtype=np.int64)
    if goal(cur0):
        return []
    options: list[tuple[list[Move], NDArray[Any]]] = []
    for auf in _AUFS:
        for text in algs.values():
            seq = _alg(f"{auf} {text}".strip())
            options.append((seq, _perm(seq)))
    finals = [(_alg(a) if a else [], _perm(_alg(a) if a else [])) for a in _AUFS]

    for looks in range(1, max_looks + 1):
        best: list[Move] | None = None
        for combo in itertools.product(options, repeat=looks):
            cur = cur0
            for _, perm in combo:
                cur = cur[perm]
            tail: list[Move] = []
            if final_auf:
                for seq, perm in finals:
                    if goal(cur[perm]):
                        tail = seq
                        break
                else:
                    continue
            elif not goal(cur):
                continue
            moves = _merge([m for seq, _ in combo for m in seq] + tail)
            if best is None or len(moves) < len(best):
                best = moves
        if best is not None:
            return best
    raise ValueError("CFOP: could not finish a last-layer step")


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def solve_cfop(state: CubeState) -> list[Stage]:
    """Solve ``state`` with the CFOP method, returned as labelled stages.

    Stages that need no moves are left out. Applying every stage's moves in
    order solves the cube.

    Raises
    ------
    ValueError
        If the state is not a valid, solvable cube.
    """
    if state.is_solved():
        return []
    if not is_valid_state(state):
        raise ValueError("Invalid cube state: not solvable.")

    stages: list[Stage] = []

    def add(name: str, moves: Sequence[Move]) -> None:
        if moves:
            stages.append(Stage(name, tuple(moves)))

    cross = _merge(_solve_cross(state))
    add("CROSS", cross)
    state = _apply(state, cross)

    for stage in _solve_f2l(state):
        stages.append(stage)
        state = _apply(state, stage.moves)

    for name, algs, goal, looks, auf in (
        ("OLL edges", _OLL_EDGE_ALGS, _edges_oriented, 3, False),
        ("OLL corners", _OLL_CORNER_ALGS, _top_oriented, 3, False),
        ("PLL corners", _PLL_CORNER_ALGS, _corners_placed, 2, True),
        ("PLL edges", _PLL_EDGE_ALGS, _all_solved, 3, True),
    ):
        moves = _look_search(state, algs, goal, looks, auf)
        add(name, moves)
        state = _apply(state, moves)

    if not state.is_solved():  # pragma: no cover - defensive
        raise ValueError("CFOP: internal error, cube not solved")
    return stages
