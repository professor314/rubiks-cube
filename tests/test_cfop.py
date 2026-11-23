"""Tests for the CFOP solver (cross, F2L, 2-look OLL, 2-look PLL)."""

from __future__ import annotations

import random

import pytest

np = pytest.importorskip("numpy")

from rubiks_cube import cfop
from rubiks_cube.controller import CubeController
from rubiks_cube.cube_state import CubeState
from rubiks_cube.moves import Move, apply_move, apply_sequence


def _scrambled(seed: int, length: int = 25) -> CubeState:
    rng = random.Random(seed)
    seq: list[Move] = []
    last = ""
    while len(seq) < length:
        face = rng.choice("UDLRFB")
        if face != last:
            last = face
            seq.append(Move(face + rng.choice(["", "'", "2"])))
    return apply_sequence(CubeState.solved(), seq)


def test_sticker_tables_describe_real_pieces() -> None:
    """Every move must carry each edge/corner's stickers onto one other piece."""
    slots = [set(s) for s in cfop._PIECES.values()]
    tables = cfop._move_tables()
    for move, table in tables.items():
        for slot in slots:
            moved = {table[i] for i in slot}
            assert moved in slots, (move, slot)


def test_solved_cube_needs_no_moves() -> None:
    assert cfop.solve_cfop(CubeState.solved()) == []


@pytest.mark.parametrize("seed", range(40))
def test_cfop_solves_random_scrambles(seed: int) -> None:
    state = _scrambled(seed)
    for stage in cfop.solve_cfop(state):
        state = apply_sequence(state, list(stage.moves))
    assert state.is_solved()


def test_each_stage_keeps_what_earlier_stages_built() -> None:
    state = _scrambled(1234)
    seen: list[str] = []
    for stage in cfop.solve_cfop(state):
        state = apply_sequence(state, list(stage.moves))
        f = state.facelets
        seen.append(stage.name.split()[0])
        if stage.name == "CROSS":
            for face_row_col in ((1, 0, 1), (1, 1, 0), (1, 1, 2), (1, 2, 1)):
                assert f[face_row_col] == 1
            for face, idx in ((4, (2, 1)), (3, (2, 1)), (5, (2, 1)), (2, (2, 1))):
                assert f[face, idx[0], idx[1]] == face
        if stage.name.startswith("F2L 4/4"):
            assert (f[1] == 1).all()  # whole D face
            for face in (2, 3, 4, 5):  # bottom two rows of every side face
                assert (f[face, 1:, :] == face).all()
        if stage.name == "OLL corners":
            assert (f[0] == 0).all()  # whole U face
    assert state.is_solved()
    assert seen[0] == "CROSS"
    assert seen.index("OLL") < seen.index("PLL")


def test_stage_names_and_order() -> None:
    names = [s.name for s in cfop.solve_cfop(_scrambled(99))]
    order = ["CROSS", "F2L", "OLL edges", "OLL corners", "PLL corners", "PLL edges"]
    positions = [
        next(i for i, n in enumerate(order) if n == name or name.startswith(n))
        for name in names
    ]
    assert positions == sorted(positions)


def test_last_layer_only_states() -> None:
    """Cases that only need OLL/PLL (everything below is already solved)."""
    from rubiks_cube.moves import parse_move_string

    for text in (
        "R U R' U R U2 R'",
        "F R U R' U' F'",
        "R U R' U' R' F R2 U' R' U' R U R' F'",
        "R2 U R U R' U' R' U' R' U R'",
    ):
        state = apply_sequence(CubeState.solved(), parse_move_string(text))
        for stage in cfop.solve_cfop(state):
            assert not stage.name.startswith(("CROSS", "F2L"))
            state = apply_sequence(state, list(stage.moves))
        assert state.is_solved()


def test_invalid_cube_is_rejected() -> None:
    facelets = CubeState.solved().facelets.copy()
    facelets[0, 0, 0] = 5  # one sticker the wrong colour
    with pytest.raises(ValueError):
        cfop.solve_cfop(CubeState(facelets))


def test_controller_solve_stages() -> None:
    controller = CubeController()
    controller.scramble(25)
    for method in ("cfop", "kociemba"):
        stages = controller.solve_stages(method)
        state = controller.state
        for stage in stages:
            state = apply_sequence(state, list(stage.moves))
        assert state.is_solved()
    with pytest.raises(ValueError):
        controller.solve_stages("nope")


def test_merge_combines_same_face_turns() -> None:
    u, ui, r = Move.U, Move.U_PRIME, Move.R
    assert cfop._merge([u, u]) == [Move.U2]
    assert cfop._merge([u, ui]) == []
    assert cfop._merge([r, u, ui, r]) == [Move.R2]
    assert apply_move(CubeState.solved(), Move.U2) == apply_sequence(
        CubeState.solved(), [u, u]
    )
