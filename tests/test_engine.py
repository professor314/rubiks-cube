"""Tests for the numpy-backed cube engine (state, moves, scrambler, validation).

These require numpy. In environments without it (e.g. a restricted sandbox)
the whole module is skipped; CI installs numpy and runs them in full.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from rubiks_cube.cube_state import CubeState
from rubiks_cube.moves import (
    Move,
    apply_move,
    apply_sequence,
    inverse_move,
    inverse_sequence,
    move_to_string,
    parse_move_string,
)
from rubiks_cube.scrambler import generate_scramble
from rubiks_cube.validation import is_valid_state

ALL_MOVES = list(Move)


# --------------------------------------------------------------------------- #
# CubeState
# --------------------------------------------------------------------------- #
def test_solved_is_solved() -> None:
    assert CubeState.solved().is_solved()


def test_solved_facelets_shape() -> None:
    assert CubeState.solved().facelets.shape == (6, 3, 3)


def test_state_is_immutable() -> None:
    state = CubeState.solved()
    with pytest.raises((ValueError, RuntimeError)):
        state.facelets[0, 0, 0] = 5


def test_kociemba_string_round_trip() -> None:
    state = CubeState.solved()
    restored = CubeState.from_kociemba_string(state.to_kociemba_string())
    assert restored == state


def test_equality_and_hash() -> None:
    a = CubeState.solved()
    b = CubeState.solved()
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


# --------------------------------------------------------------------------- #
# Moves — algebraic properties
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("move", ALL_MOVES)
def test_move_then_inverse_restores(move: Move) -> None:
    state = CubeState.solved()
    out = apply_move(apply_move(state, move), inverse_move(move))
    assert out.is_solved()


@pytest.mark.parametrize("move", ALL_MOVES)
def test_four_quarter_turns_identity(move: Move) -> None:
    # Applying any single move four times returns to start (period divides 4).
    state = CubeState.solved()
    for _ in range(4):
        state = apply_move(state, move)
    assert state.is_solved()


@pytest.mark.parametrize("face", ["U", "D", "L", "R", "F", "B"])
def test_double_move_equals_two_singles(face: str) -> None:
    single = Move(face)
    double = Move(face + "2")
    solved = CubeState.solved()
    via_double = apply_move(solved, double)
    via_two = apply_move(apply_move(solved, single), single)
    assert via_double == via_two


def test_move_changes_state() -> None:
    assert not apply_move(CubeState.solved(), Move.U).is_solved()


def test_sequence_and_inverse_restores() -> None:
    state = CubeState.solved()
    seq = [Move.U, Move.R, Move.F, Move.D_PRIME, Move.L2]
    scrambled = apply_sequence(state, seq)
    restored = apply_sequence(scrambled, inverse_sequence(seq))
    assert restored.is_solved()


def test_sexy_move_six_times_identity() -> None:
    # (R U R' U') has order 6 on a solved cube — a classic invariant.
    state = CubeState.solved()
    sexy = [Move.R, Move.U, Move.R_PRIME, Move.U_PRIME]
    for _ in range(6):
        state = apply_sequence(state, sexy)
    assert state.is_solved()


# --------------------------------------------------------------------------- #
# Notation parsing
# --------------------------------------------------------------------------- #
def test_parse_and_stringify_round_trip() -> None:
    text = "U R' F2 D L2 B'"
    assert move_to_string(parse_move_string(text)) == text


def test_parse_empty() -> None:
    assert parse_move_string("") == []


def test_parse_invalid_raises() -> None:
    with pytest.raises(ValueError):
        parse_move_string("U X2")


# --------------------------------------------------------------------------- #
# Scrambler
# --------------------------------------------------------------------------- #
def test_scramble_length() -> None:
    assert len(generate_scramble(20)) == 20


def test_scramble_no_consecutive_same_face() -> None:
    moves = generate_scramble(50)
    faces = [m.value[0] for m in moves]
    for i in range(1, len(faces)):
        assert faces[i] != faces[i - 1]


def test_scramble_is_applicable_and_reversible() -> None:
    state = CubeState.solved()
    scramble = generate_scramble(25)
    scrambled = apply_sequence(state, scramble)
    restored = apply_sequence(scrambled, inverse_sequence(scramble))
    assert restored.is_solved()


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_solved_state_is_valid() -> None:
    assert is_valid_state(CubeState.solved())


def test_scrambled_state_is_valid() -> None:
    state = apply_sequence(CubeState.solved(), generate_scramble(20))
    assert is_valid_state(state)
