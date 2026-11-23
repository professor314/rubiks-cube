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

The controls are always listed in a panel on the left of the window (press **`?`** to hide or show it).

## Controls

| Key | Action | | Key | Action |
|-----|--------|-|-----|--------|
| `u d l r f b` | Clockwise face turns | | `s` | Scramble |
| `i k j ; h n` | Counter-clockwise (U' D' L' R' F' B') | | `space` | Solve |
| `z` | Undo | | `y` | Redo |
| `t` | Toggle trainer mode | | `?` | Hide/show the controls panel |
| `m` | Switch solver (Kociemba / CFOP) | | | |
| `q` | Quit | | mouse drag | Rotate the 3D view |

On-screen buttons (**Scramble / Solve / Reset / Undo / Redo / Trainer**) mirror
the keyboard actions.

## Solve

**Solve** (`space`) solves the cube from wherever it is. It shows the move list in
the window and plays the moves one at a time with the current move in
`[brackets]`. The full list is also printed to the terminal. A solve made this
way is never timed or saved to your trainer stats.

Pick the solving method with the **Solver** button or the **`m`** key:

| Solver | What it does | Typical length |
|--------|--------------|----------------|
| **Kociemba** (default) | Two-phase algorithm; near-shortest solution. Needs `pip install -e ".[solver]"`. | about 20 moves |
| **CFOP** | The speedcubing method, step by step (see below). No extra install. | about 55 to 90 moves |

### CFOP steps

1. **CROSS**: the four bottom (D) edges, found optimally.
2. **F2L**: the four corner+edge pairs of the first two layers, one pair at a
   time (the pair that needs the fewest moves goes first). Each pair is found by
   search, keeping the cross and earlier pairs intact, so the moves are valid and
   human-like but are not always the textbook F2L algorithms.
3. **OLL (2-look)**: first orient the top edges, then the top corners, with the
   standard algorithms (Sune, Anti-Sune, H, Pi, U, T, L, and two edge algorithms).
4. **PLL (2-look)**: first place the top corners, then the top edges (with a final
   U turn), using T, Y, Ja, Ua, Ub, H and Jb permutations.

The window shows the current stage name above the moves, and a per-stage move
count when the solve finishes.

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
├── solver.py       # Optional Kociemba wrapper (shortest solution)
├── cfop.py         # CFOP solver: cross, F2L, 2-look OLL, 2-look PLL
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
