"""Interactive 3D Rubik's cube application (matplotlib).

Ties together the engine (:mod:`rubiks_cube.controller`), the renderer
(:mod:`rubiks_cube.render`), and the practice stats (:mod:`rubiks_cube.stats`,
:mod:`rubiks_cube.session`) into a single interactive window with:

- animated face turns,
- on-screen buttons (Scramble / Solve / Reset / Undo / Redo / Trainer),
- a solver that shows its move list in the window and animates it,
- keyboard controls, always listed in a panel on the left of the window,
- a live HUD (state, last move, move count, timer),
- trainer mode: timed solves recorded to a persistent stats file with
  ao5 / ao12 / personal-best display.

numpy and matplotlib are imported lazily so importing this module never fails
in environments without them; only :func:`run_rubiks_cube` requires them.
"""

from __future__ import annotations

import textwrap
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
    "u": "U",
    "d": "D",
    "l": "L",
    "r": "R",
    "f": "F",
    "b": "B",
    "i": "U'",
    "k": "D'",
    "j": "L'",
    ";": "R'",
    "h": "F'",
    "n": "B'",
}

_CONTROLS_TEXT = (
    "CONTROLS\n"
    "\n"
    "Turn a face clockwise\n"
    "  u d l r f b\n"
    "\n"
    "Turn counter-clockwise\n"
    "  i = U'   k = D'   j = L'\n"
    "  ; = R'   h = F'   n = B'\n"
    "\n"
    "  s      scramble\n"
    "  space  solve (shows moves)\n"
    "  z      undo\n"
    "  y      redo\n"
    "  t      trainer on/off\n"
    "  ?      hide/show this panel\n"
    "  q      quit\n"
    "  mouse  drag to rotate view\n"
    "\n"
    "U up  D down  L left\n"
    "R right  F front  B back\n"
    "\n"
    "TRAINER: s starts a timed solve,\n"
    "the timer stops when you solve\n"
    "it. Using Solve does not count."
)

_SOLUTION_WRAP = 46  # characters per line in the on-screen solution box

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
    fig = plt.figure(figsize=(11.0, 8.0), num="Rubik's Cube")
    fig.patch.set_facecolor("#0E0F12")
    ax = fig.add_axes((0.26, 0.30, 0.74, 0.70), projection="3d")
    ax.set_facecolor("#0E0F12")

    renderer = CubeRenderer(ax)
    renderer.draw(controller.state)

    hud = fig.text(
        0.63,
        0.165,
        "",
        ha="center",
        va="top",
        fontsize=10,
        family="monospace",
        color="#E8E8E8",
    )
    # Controls are always visible (press ? to hide/show).
    controls_box = fig.text(
        0.015,
        0.975,
        _CONTROLS_TEXT,
        ha="left",
        va="top",
        fontsize=9,
        family="monospace",
        color="#D5D9E0",
        bbox={"boxstyle": "round", "facecolor": "#1C1F24", "edgecolor": "#3A3F47"},
    )
    # Move list shown while / after the solver runs.
    solution_box = fig.text(
        0.63,
        0.29,
        "",
        ha="center",
        va="top",
        fontsize=10,
        family="monospace",
        color="#8BE9FD",
    )

    ui: dict[str, Any] = {
        "timer_start": None,
        "trainer": False,
        "last_move": "-",
        "animating": False,
        "busy": False,  # True for the whole solver playback
    }

    # --- helpers -----------------------------------------------------------
    def _fmt(t: float) -> str:
        return f"{t:.2f}s" if t != float("inf") else "DNF"

    def _refresh_hud() -> None:
        solved = controller.is_solved()
        state_s = "SOLVED" if solved else "scrambled"
        timer_s = ""
        if ui["timer_start"] is not None:
            timer_s = f" | time {time.perf_counter() - ui['timer_start']:.1f}s"
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
            line2 = "\n(press t for trainer mode)"
        hud.set_text(line1 + line2)

    def _redraw() -> None:
        renderer.draw(controller.state)
        _refresh_hud()
        fig.canvas.draw_idle()

    def _locked() -> bool:
        """True while a move animation or the solver playback is running."""
        return bool(ui["animating"] or ui["busy"])

    def _play_move(move: Move) -> None:
        """Animate one move, then apply it to the cube and redraw."""
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

    def _animate_move(move: Move) -> None:
        """Animate a single turn requested by the user (ignored while busy)."""
        if _locked():
            return
        _play_move(move)

    def _solution_text(names: list[str], done: int, note: str = "") -> str:
        """Wrapped move list with the move being played marked in [brackets]."""
        marked = [f"[{n}]" if i == done else n for i, n in enumerate(names)]
        header = f"SOLUTION ({len(names)} moves, {min(done, len(names))} done)"
        body = textwrap.fill(" ".join(marked), width=_SOLUTION_WRAP)
        return header + "\n" + body + (f"\n{note}" if note else "")

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
        if _locked():
            return
        solution_box.set_text("")
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
        if _locked() or controller.is_solved():
            return
        try:
            solution = controller.solve()
        except ImportError:
            msg = "Solver unavailable. Install with: pip install kociemba"
            print(msg)
            solution_box.set_text(msg)
            fig.canvas.draw_idle()
            return
        except ValueError as exc:
            print(f"Cannot solve: {exc}")
            solution_box.set_text(f"Cannot solve: {exc}")
            fig.canvas.draw_idle()
            return
        names = [m.value for m in solution]
        print(f"Solution ({len(solution)} moves): {move_to_string(solution)}")
        # A solver-made solve never counts as a timed attempt.
        ui["timer_start"] = None
        ui["busy"] = True
        try:
            for i, mv in enumerate(solution):
                if not plt.fignum_exists(fig.number):
                    return
                solution_box.set_text(_solution_text(names, i))
                _play_move(mv)
            solution_box.set_text(
                _solution_text(names, len(names), "Solved! (not timed)")
            )
        finally:
            ui["busy"] = False
        ui["last_move"] = "solve"
        _redraw()

    def do_reset(_evt: Any = None) -> None:
        if _locked():
            return
        solution_box.set_text("")
        controller.reset()
        ui["timer_start"] = None
        ui["last_move"] = "-"
        _redraw()

    def do_undo(_evt: Any = None) -> None:
        if _locked():
            return
        mv = controller.undo()
        if mv is not None:
            ui["last_move"] = f"undo {mv.value}"
            _redraw()

    def do_redo(_evt: Any = None) -> None:
        if _locked():
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
    width = 0.115
    for idx, (label, cb) in enumerate(button_specs):
        bx = 0.26 + idx * (width + 0.005)
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
            controls_box.set_visible(not controls_box.get_visible())
            fig.canvas.draw_idle()
        elif key == "q":
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)

    _refresh_hud()
    print("=" * 52)
    print("  Rubik's Cube — Interactive 3D")
    print("  Controls are listed in the window (press ? to hide/show).")
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
