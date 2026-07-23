# Rubik's Cube — Interactive 3D

A 3D interactive Rubik's cube built with matplotlib. Features keyboard controls for face rotations, a random scramble generator, solve timer, and optional Kociemba solver integration.

## Install

```bash
pip install -e .
# For solver support:
pip install -e ".[solver]"
```

## Run

```bash
rubiks-cube
```

Or:
```bash
python -m rubiks_cube.cube_viz
```

## Controls

| Key | Action |
|-----|--------|
| u, d, l, r, f, b | Clockwise face rotation |
| i, k, j, ;, h, n | Counter-clockwise (U', D', L', R', F', B') |
| Shift + letter | Counter-clockwise (alternative) |
| s | Scramble (random 20 moves, starts timer) |
| Space | Solve (requires kociemba) |
| Mouse drag | Rotate 3D view |

## Project Structure

```
rubiks_cube/
├── __init__.py        # Package exports
├── cube_state.py      # CubeState (6,3,3) facelet representation
├── moves.py           # Move enum, apply_move, inverse, parse
├── validation.py      # Solvability checker
├── scrambler.py       # Random scramble generator
├── timer.py           # Solve timer
├── solver.py          # Kociemba solver wrapper
└── cube_viz.py        # 3D visualization + keyboard controls
```
