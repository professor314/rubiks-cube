"""The 3D drawing must agree with the engine's cube state.

Builds a small physical model from the renderer's own geometry (each sticker's
3D position), turns layers the way a real cube turns, and checks that the
engine's facelet array ends up with the same colour at every drawn position.
This catches a face being drawn flipped (e.g. U/D front-to-back).
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from rubiks_cube import render
from rubiks_cube.cube_state import CubeState
from rubiks_cube.moves import Move, apply_move
from rubiks_cube.scrambler import generate_scramble

_FACE_OF = {"U": 0, "D": 1, "L": 2, "R": 3, "F": 4, "B": 5}
_ALL = [(f, r, c) for f in range(6) for r in range(3) for c in range(3)]
_VERTS = {k: render.facelet_vertices(*k) for k in _ALL}
_CENTER = {k: _VERTS[k].mean(axis=0) for k in _ALL}


def _key_at(point: np.ndarray) -> tuple[int, int, int]:
    for key in _ALL:
        if np.allclose(_CENTER[key], point, atol=1e-6):
            return key
    raise AssertionError(f"no facelet at {point}")


def _physical_turn(colors: dict, move: Move) -> dict:
    face = _FACE_OF[move.value[0]]
    quarters = (
        2 if move.value.endswith("2") else (-1 if move.value.endswith("'") else 1)
    )
    angle = render._FACE_CW_SIGN[face] * (np.pi / 2) * quarters
    rot = render.rotation_matrix(render._FACE_AXIS[face], angle)
    out: dict = {}
    for key in _ALL:
        if render._facelet_belongs_to_layer(_VERTS[key], face):
            out[_key_at(rot @ _CENTER[key])] = colors[key]
        else:
            out[key] = colors[key]
    return out


def _agrees(sequence: list[Move]) -> bool:
    colors = {k: k[0] for k in _ALL}
    state = CubeState.solved()
    for move in sequence:
        colors = _physical_turn(colors, move)
        state = apply_move(state, move)
    return {k: int(state.facelets[k]) for k in _ALL} == colors


@pytest.mark.parametrize("move", list(Move), ids=lambda m: m.value)
def test_each_move_matches_the_drawn_cube(move: Move) -> None:
    assert _agrees([move])


def test_random_scrambles_match_the_drawn_cube() -> None:
    for _ in range(10):
        assert _agrees(generate_scramble(20))
