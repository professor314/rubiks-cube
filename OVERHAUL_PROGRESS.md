# Rubik's Cube Overhaul — Progress Log

Branch: `feature/ui-and-trainer-overhaul`

## Environment constraints (sandbox)
- No `numpy` / `matplotlib`, no network to install them.
- Available: pytest, black, ruff, mypy, pyright.
- Strategy: new trainer/stats logic is **pure-Python** (tested & passing here).
  Engine tests and UI are lint/type-checked here and verified by CI + your desktop.

## Timeblock plan (~15 min each)
- [ ] **TB1** — Trainer/stats core module (pure-Python) + unit tests passing locally
- [ ] **TB2** — Session/stats persistence (JSON) + scramble-of-the-day + tests
- [ ] **TB3** — Engine test suite (cube_state, moves, scrambler, validation) [CI-run]
- [ ] **TB4** — Rendering overhaul: animation + better materials/HUD
- [ ] **TB5** — UX: on-screen buttons, undo/redo, reset, help overlay
- [ ] **TB6** — Wire trainer mode into the app UI
- [ ] **TB7** — GitHub Actions CI (pytest + ruff + mypy) + ruff/black config
- [ ] **TB8** — README overhaul, docstrings, final lint/type pass, open PR

## Completed log
(entries added as each timeblock finishes)
