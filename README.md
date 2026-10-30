# Rubik's Cube — Interactive 3D + Trainer

An interactive 3D Rubik's cube built with matplotlib, featuring **animated face
turns**, on-screen controls, undo/redo, an optional Kociemba solver, and a
**practice trainer** that records your solve times with speedcubing stats
(ao5 / ao12 / personal best).

## Features

- 🧊 **Animated 3D cube** — smooth layer-turn animation, clean speedcube palette
- ⌨️ **Keyboard + on-screen buttons** — turn any face, scramble, solve, reset
- ↩️ **Undo / redo** full move history
- ⏱️ **Trainer mode** — timed solves with a deterministic *scramble of the day*
- 📊 **Persistent stats** — ao5, ao12, best single, saved to `~/.rubiks_cube/stats.json`
- 🧮 **Optional solver** — near-optimal solutions via the `kociemba` two-phase algorithm
- ✅ **Tested & typed** — pytest suite, ruff, mypy, CI across Python 3.10–3.13

## Install

```bash
pip install -e .
# Optional: enable the Kociemba solver
pip install -e ".[solver]"
# For development (tests, lint, type-check):
pip install -e ".[dev]"
```

## Run

```bash
rubiks-cube
# or
python -m rubiks_cube.cube_viz
```

Press **`?`** in the window at any time for the full control list.

## Controls

| Key | Action | | Key | Action |
|-----|--------|-|-----|--------|
| `u d l r f b` | Clockwise face turns | | `s` | Scramble |
| `i k j ; h n` | Counter-clockwise (U' D' L' R' F' B') | | `space` | Solve |
| `z` | Undo | | `y` | Redo |
| `t` | Toggle trainer mode | | `?` | Toggle help overlay |
| `q` | Quit | | mouse drag | Rotate the 3D view |

On-screen buttons (**Scramble / Solve / Reset / Undo / Redo / Trainer**) mirror
the keyboard actions.

## Trainer mode

Press **`t`** to enter trainer mode, then **`s`** to start a timed solve against
the day's scramble. The timer stops automatically when the cube is solved and
the result is appended to your stats file. The HUD shows live **ao5**, **ao12**,
and **best** — using the WCA average definition (drop best & worst, mean the
rest; a DNF counts as the worst).

## Project structure

```
rubiks_cube/
├── __init__.py     # Lazy public API (PEP 562) — import light modules w/o numpy
├── cube_state.py   # CubeState: (6,3,3) facelet model
├── moves.py        # 18 moves, apply/inverse/parse
├── validation.py   # Solvability checker
├── scrambler.py    # WCA-style random scrambles
├── timer.py        # Solve timer
├── solver.py       # Optional Kociemba wrapper
├── render.py       # CubeRenderer: 3D drawing + turn animation
├── controller.py   # State + undo/redo/scramble/reset/solve (GUI-free logic)
├── stats.py        # SolveStats: ao5/ao12/best, DNF, JSON (pure-Python)
├── session.py      # Persistence + deterministic scramble-of-the-day
└── cube_viz.py     # Interactive app: buttons, help, animation, trainer HUD
```

## Development

```bash
pytest          # run the test suite
ruff check .    # lint
ruff format .   # format
mypy rubiks_cube  # type-check
```

The test suite is split so the pure-Python logic (`stats`, `session`, `render`
helpers) runs anywhere, while numpy-backed engine tests are skipped where numpy
is unavailable and run in full in CI.

## License

MIT
