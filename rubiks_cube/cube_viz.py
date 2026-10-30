"""Interactive 3D Rubik's cube application (matplotlib).

Ties together the engine (:mod:`rubiks_cube.controller`), the renderer
(:mod:`rubiks_cube.render`), and the practice stats (:mod:`rubiks_cube.stats`,
:mod:`rubiks_cube.session`) into a single interactive window with:

- animated face turns,
- on-screen buttons (Scramble / Solve / Reset / Undo / Redo / Trainer),
- keyboard controls with a toggleable help overlay,
- a live HUD (state, last move, move count, timer),
- trainer mode: timed solves recorded to a persistent stats file with
  ao5 / ao12 / personal-best display.

numpy and matplotlib are imported lazily so importing this module never fails
in environments without them; only :func:`run_rubiks_cube` requires them.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .controller import CubeController
from .render import CubeRenderer
from .session import SessionStore, scramble_of_the_day
from .stats import Solve, SolveStats

if TYPE_CHECKING:  # pragma: no cover
    from .moves import Move

# Keyboard: key -> move notation. Lowercase = CW, mapped set = CCW.
_KEY_TO_MOVE_STR: dict[str, str] = {
    "u": "U", "d": "D", "l": "L", "r": "R", "f": "F", "b": "B",
    "i": "U'", "k": "D'", "j": "L'", ";": "R'", "h": "F'", "n": "B'",
}

_HELP_TEXT = (
    "KEYBOARD\n"
    "  u d l r f b   clockwise face turns\n"
    "  i k j ; h n   counter-clockwise (U' D' L' R' F' B')\n"
    "  s   scramble        space  solve\n"
    "  z   undo            y      redo\n"
    "  t   toggle trainer  ?      toggle this help\n"
    "  q   quit\n\n"
    "BUTTONS below the cube do the same actions.\n"
    "TRAINER: press s to start a timed solve; the timer\n"
    "stops when the cube is solved and the result is saved."
)

_ANIM_FRAMES = 8  # frames per quarter turn (higher = smoother/slower)
_ANIM_PAUSE = 0.012  # seconds between frames


def run_rubiks_cube() -> None:
    """Launch the interactive 3D Rubik's cube application."""
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button

    from .moves import Move, move_to_string

    _ensure_move_tables()
    controller = CubeController()
    store = SessionStore()
    stats: SolveStats = store.load()

    # --- figure layout -----------------------------------------------------
    fig = plt.figure(figsize=(8.5, 8.0), num="Rubik's Cube")
    fig.patch.set_facecolor("#0E0F12")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0E0F12")
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.16)

    renderer = CubeRenderer(ax)
    renderer.draw(controller.state)

    hud = fig.text(
        0.5, 0.135, "", ha="center", va="top", fontsize=10,
        family="monospace", color="#E8E8E8",
    )
    help_box = fig.text(
        0.5, 0.5, _HELP_TEXT, ha="center", va="center", fontsize=10,
        family="monospace", color="#F2F2F2",
        bbox={"boxstyle": "round", "facecolor": "#1C1F24", "edgecolor": "#3A3F47"},
        visible=False,
    )

    ui: dict[str, Any] = {
        "timer_start": None,
        "trainer": False,
        "last_move": "-",
        "animating": False,
    }

    # --- helpers -----------------------------------------------------------
    def _fmt(t: float) -> str:
        return f"{t:.2f}s" if t != float("inf") else "DNF"

    def _refresh_hud() -> None:
        solved = controller.is_solved()
        state_s = "SOLVED" if solved else "scrambled"
        timer_s = ""
        if ui["timer_start"] is not None:
            timer_s = f" | ⏱ {time.perf_counter() - ui['timer_start']:.1f}s"
        line1 = (
            f"{state_s}  |  last: {ui['last_move']}  |  moves: "
            f"{controller.move_count}{timer_s}"
        )
        if ui["trainer"]:
            line2 = (
                f"\nTRAINER  solves:{stats.count}  "
                f"best:{_fmt(stats.best)}  "
                f"ao5:{_fmt(stats.ao5())}  ao12:{_fmt(stats.ao12())}"
            )
        else:
            line2 = "\n(press t for trainer mode, ? for help)"
        hud.set_text(line1 + line2)

    def _redraw() -> None:
        renderer.draw(controller.state)
        _refresh_hud()
        fig.canvas.draw_idle()

    def _animate_move(move: Move) -> None:
        """Animate a single quarter/half turn, then apply it logically."""
        if ui["animating"]:
            return
        ui["animating"] = True
        face = _FACE_OF_MOVE[move]
        qt = _QUARTER_TURNS[move]
        pre_state = controller.state
        try:
            for frame in range(1, _ANIM_FRAMES + 1):
                angle = CubeRenderer.turn_angle(face, qt, frame / _ANIM_FRAMES)
                renderer.draw_mid_turn(pre_state, face, angle)
                fig.canvas.draw_idle()
                plt.pause(_ANIM_PAUSE)
        finally:
            ui["animating"] = False
        controller.apply(move)
        ui["last_move"] = move.value
        _redraw()

    def _record_solve_if_done() -> None:
        if ui["timer_start"] is not None and controller.is_solved():
            elapsed = time.perf_counter() - ui["timer_start"]
            ui["timer_start"] = None
            if ui["trainer"]:
                stats.add(Solve(time=elapsed, timestamp=time.time()))
                store.save(stats)
                print(f"Solve recorded: {elapsed:.2f}s  (ao5 {_fmt(stats.ao5())})")
            else:
                print(f"Solved in {elapsed:.2f}s")

    # --- action callbacks --------------------------------------------------
    def do_scramble(_evt: Any = None) -> None:
        if ui["animating"]:
            return
        if ui["trainer"]:
            # Deterministic daily scramble in trainer mode.
            from .moves import parse_move_string

            seq = parse_move_string(scramble_of_the_day())
            controller.reset()
            for mv in seq:
                controller.apply(mv, user_move=False)
            controller.history.clear()
            controller.move_count = 0
            print(f"Daily scramble: {move_to_string(seq)}")
        else:
            seq = controller.scramble(20)
            print(f"Scramble: {move_to_string(seq)}")
        ui["last_move"] = "scramble"
        ui["timer_start"] = time.perf_counter()
        _redraw()

    def do_solve(_evt: Any = None) -> None:
        if ui["animating"] or controller.is_solved():
            return
        try:
            solution = controller.solve()
        except ImportError:
            print("Solver unavailable. Install with: pip install kociemba")
            return
        print(f"Solution ({len(solution)} moves): {move_to_string(solution)}")
        controller.apply_solution(solution)
        ui["last_move"] = "solve"
        _record_solve_if_done()
        _redraw()

    def do_reset(_evt: Any = None) -> None:
        if ui["animating"]:
            return
        controller.reset()
        ui["timer_start"] = None
        ui["last_move"] = "-"
        _redraw()

    def do_undo(_evt: Any = None) -> None:
        if ui["animating"]:
            return
        mv = controller.undo()
        if mv is not None:
            ui["last_move"] = f"undo {mv.value}"
            _redraw()

    def do_redo(_evt: Any = None) -> None:
        if ui["animating"]:
            return
        mv = controller.redo()
        if mv is not None:
            ui["last_move"] = f"redo {mv.value}"
            _redraw()

    def do_toggle_trainer(_evt: Any = None) -> None:
        ui["trainer"] = not ui["trainer"]
        print(f"Trainer mode: {'ON' if ui['trainer'] else 'off'}")
        _refresh_hud()
        fig.canvas.draw_idle()

    # --- buttons -----------------------------------------------------------
    button_specs = [
        ("Scramble", do_scramble),
        ("Solve", do_solve),
        ("Reset", do_reset),
        ("Undo", do_undo),
        ("Redo", do_redo),
        ("Trainer", do_toggle_trainer),
    ]
    buttons = []  # keep refs alive
    width = 0.14
    for idx, (label, cb) in enumerate(button_specs):
        bx = 0.03 + idx * (width + 0.005)
        bax = fig.add_axes((bx, 0.03, width, 0.055))
        btn = Button(bax, label, color="#23272E", hovercolor="#30353D")
        btn.label.set_color("#F2F2F2")
        btn.on_clicked(cb)
        buttons.append(btn)

    # --- keyboard ----------------------------------------------------------
    def on_key(event: Any) -> None:
        key = event.key
        if key is None:
            return
        if key in _KEY_TO_MOVE_STR:
            _animate_move(Move(_KEY_TO_MOVE_STR[key]))
            _record_solve_if_done()
        elif key == "s":
            do_scramble()
        elif key == " ":
            do_solve()
        elif key == "z":
            do_undo()
        elif key == "y":
            do_redo()
        elif key == "t":
            do_toggle_trainer()
        elif key == "?":
            help_box.set_visible(not help_box.get_visible())
            fig.canvas.draw_idle()
        elif key == "q":
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)

    _refresh_hud()
    print("=" * 52)
    print("  Rubik's Cube — Interactive 3D")
    print("  Press ? in the window for the full control list.")
    print("=" * 52)
    plt.show()


# Lazily-populated lookup tables for animation (filled on first use so that
# importing this module stays numpy-free).
_FACE_OF_MOVE: dict[Move, int] = {}
_QUARTER_TURNS: dict[Move, int] = {}


def _ensure_move_tables() -> None:
    if _FACE_OF_MOVE:
        return
    from .cube_state import B, D, F, L, R, U
    from .moves import Move

    face_map = {"U": U, "D": D, "L": L, "R": R, "F": F, "B": B}
    for mv in Move:
        letter = mv.value[0]
        _FACE_OF_MOVE[mv] = face_map[letter]
        if mv.value.endswith("2"):
            _QUARTER_TURNS[mv] = 2
        elif mv.value.endswith("'"):
            _QUARTER_TURNS[mv] = -1
        else:
            _QUARTER_TURNS[mv] = 1


if __name__ == "__main__":  # pragma: no cover
    run_rubiks_cube()
