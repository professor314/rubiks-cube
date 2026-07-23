"""Interactive 3D Rubik's cube visualization.

Renders a 3x3x3 cube using matplotlib Poly3DCollection with keyboard
controls for face rotations, scrambling, and solving.

Run: rubiks-cube (after pip install) or py -m rubiks_cube.cube_viz
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .cube_state import CubeState, U, D, L, R, F, B
from .moves import Move, apply_move, apply_sequence, move_to_string
from .scrambler import generate_scramble

# Standard color scheme: face index → hex color
COLOR_MAP: dict[int, str] = {
    0: "#FFFFFF",  # White (U)
    1: "#FFFF00",  # Yellow (D)
    2: "#00AA00",  # Green (L)
    3: "#0000FF",  # Blue (R)
    4: "#FF0000",  # Red (F)
    5: "#FF8C00",  # Orange (B)
}

_GAP = 0.05  # gap between facelets


def _facelet_vertices(face: int, row: int, col: int) -> NDArray[np.float64]:
    """Compute 4 corner vertices of a facelet in 3D space.

    Cube spans (-1.5, -1.5, -1.5) to (1.5, 1.5, 1.5).
    """
    lo, hi = _GAP, 1.0 - _GAP

    if face == U:  # y = 1.5 plane
        x0, x1 = -1.5 + col + lo, -1.5 + col + hi
        z0, z1 = -1.5 + (2 - row) + lo, -1.5 + (2 - row) + hi
        return np.array([[x0, 1.5, z0], [x1, 1.5, z0], [x1, 1.5, z1], [x0, 1.5, z1]])

    elif face == D:  # y = -1.5 plane
        x0, x1 = -1.5 + col + lo, -1.5 + col + hi
        z0, z1 = -1.5 + row + lo, -1.5 + row + hi
        return np.array([[x0, -1.5, z0], [x1, -1.5, z0], [x1, -1.5, z1], [x0, -1.5, z1]])

    elif face == F:  # z = 1.5 plane
        x0, x1 = -1.5 + col + lo, -1.5 + col + hi
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        return np.array([[x0, y0, 1.5], [x1, y0, 1.5], [x1, y1, 1.5], [x0, y1, 1.5]])

    elif face == B:  # z = -1.5 plane (mirrored)
        x0, x1 = 1.5 - (col + hi), 1.5 - (col + lo)
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        return np.array([[x0, y0, -1.5], [x1, y0, -1.5], [x1, y1, -1.5], [x0, y1, -1.5]])

    elif face == R:  # x = 1.5 plane
        z0, z1 = 1.5 - (col + hi), 1.5 - (col + lo)
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        return np.array([[1.5, y0, z0], [1.5, y0, z1], [1.5, y1, z1], [1.5, y1, z0]])

    elif face == L:  # x = -1.5 plane
        z0, z1 = -1.5 + col + lo, -1.5 + col + hi
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        return np.array([[-1.5, y0, z0], [-1.5, y0, z1], [-1.5, y1, z1], [-1.5, y1, z0]])

    raise ValueError(f"Invalid face: {face}")


def _draw_cube(ax: Any, state: CubeState) -> None:
    """Render all 54 facelets on the 3D axes."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    ax.cla()
    verts_list = []
    colors_list = []

    for face_idx in range(6):
        for row in range(3):
            for col in range(3):
                verts_list.append(_facelet_vertices(face_idx, row, col))
                colors_list.append(COLOR_MAP[int(state.facelets[face_idx, row, col])])

    collection = Poly3DCollection(verts_list, facecolors=colors_list,
                                  edgecolors="black", linewidths=0.5)
    ax.add_collection3d(collection)
    ax.set_xlim(-2, 2)
    ax.set_ylim(-2, 2)
    ax.set_zlim(-2, 2)
    ax.set_box_aspect([1, 1, 1])
    ax.set_axis_off()
    ax.view_init(elev=25, azim=-50)


def run_rubiks_cube() -> None:
    """Launch the interactive 3D Rubik's cube."""
    import matplotlib.pyplot as plt

    state = CubeState.solved()
    move_count = 0
    last_move = "None"
    timer_start: float | None = None

    fig = plt.figure(figsize=(8, 7), num="Rubik's Cube")
    ax = fig.add_subplot(111, projection="3d")
    _draw_cube(ax, state)

    status_text = fig.text(0.5, 0.02, "", ha="center", fontsize=10, fontfamily="monospace")

    def _update_status() -> None:
        s = "Solved" if state.is_solved() else "Scrambled"
        timer_str = ""
        if timer_start is not None:
            timer_str = f" | Timer: {time.perf_counter() - timer_start:.1f}s"
        status_text.set_text(f"State: {s} | Last: {last_move} | Moves: {move_count}{timer_str}")

    _update_status()

    # Key → Move mapping
    key_map: dict[str, Move] = {
        "u": Move.U, "d": Move.D, "l": Move.L, "r": Move.R, "f": Move.F, "b": Move.B,
        "i": Move.U_PRIME, "k": Move.D_PRIME, "j": Move.L_PRIME,
        ";": Move.R_PRIME, "h": Move.F_PRIME, "n": Move.B_PRIME,
    }

    def on_key(event: Any) -> None:
        nonlocal state, move_count, last_move, timer_start

        if event.key is None:
            return
        key = event.key

        if key in key_map:
            state = apply_move(state, key_map[key])
            move_count += 1
            last_move = key_map[key].value
            if state.is_solved() and timer_start is not None:
                print(f"SOLVED in {time.perf_counter() - timer_start:.2f}s!")
                timer_start = None
            _draw_cube(ax, state)
            _update_status()
            fig.canvas.draw_idle()

        elif key == "s":
            scramble = generate_scramble(20)
            state = apply_sequence(state, scramble)
            move_count = 0
            last_move = "Scramble"
            timer_start = time.perf_counter()
            print(f"Scramble: {move_to_string(scramble)}")
            _draw_cube(ax, state)
            _update_status()
            fig.canvas.draw_idle()

        elif key == " ":
            if state.is_solved():
                print("Already solved!")
                return
            try:
                from .solver import solve
                solution = solve(state)
                print(f"Solution ({len(solution)} moves): {move_to_string(solution)}")
                state = apply_sequence(state, solution)
                move_count += len(solution)
                last_move = "Solved"
                if timer_start:
                    print(f"Time: {time.perf_counter() - timer_start:.2f}s")
                    timer_start = None
                _draw_cube(ax, state)
                _update_status()
                fig.canvas.draw_idle()
            except ImportError:
                print("kociemba not installed. Run: pip install kociemba")

    fig.canvas.mpl_connect("key_press_event", on_key)

    print("=" * 50)
    print("  Rubik's Cube — Interactive 3D")
    print("  u/d/l/r/f/b = CW | i/k/j/;/h/n = CCW")
    print("  s = scramble | space = solve")
    print("=" * 50)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08)
    plt.show()


if __name__ == "__main__":
    run_rubiks_cube()
