"""Tests for the rendering module.

The geometry/animation helpers need numpy; those tests skip without it. A
dependency-free consistency check (local face constants vs. the engine's) runs
only where numpy is available, since importing cube_state requires it.
"""

from __future__ import annotations

import math

import pytest

from rubiks_cube import render


def test_color_map_covers_six_faces() -> None:
    assert sorted(render.COLOR_MAP) == [0, 1, 2, 3, 4, 5]


def test_face_axis_and_sign_tables_complete() -> None:
    for f in range(6):
        assert f in render._FACE_AXIS
        assert f in render._FACE_CW_SIGN
        assert f in render._FACE_LAYER_COORD


def test_turn_angle_endpoints() -> None:
    # At t=0 the angle is 0; at t=1 it is a full quarter turn (magnitude pi/2).
    pytest.importorskip("numpy")
    assert render.CubeRenderer.turn_angle(0, 1, 0.0) == 0.0
    assert math.isclose(
        abs(render.CubeRenderer.turn_angle(0, 1, 1.0)), math.pi / 2, rel_tol=1e-9
    )


def test_turn_angle_half_turn_magnitude() -> None:
    pytest.importorskip("numpy")
    assert math.isclose(
        abs(render.CubeRenderer.turn_angle(4, 2, 1.0)), math.pi, rel_tol=1e-9
    )


def test_local_face_constants_match_engine() -> None:
    # cube_state imports numpy, so this only runs where numpy is present.
    pytest.importorskip("numpy")
    from rubiks_cube import cube_state as cs

    assert (render.U, render.D, render.L, render.R, render.F, render.B) == (
        cs.U,
        cs.D,
        cs.L,
        cs.R,
        cs.F,
        cs.B,
    )


def test_rotation_matrix_is_orthonormal() -> None:
    np = pytest.importorskip("numpy")
    m = render.rotation_matrix(1, math.pi / 3)
    # R @ R.T == I for a proper rotation
    assert np.allclose(m @ m.T, np.eye(3))
    assert math.isclose(float(np.linalg.det(m)), 1.0, rel_tol=1e-9)
