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
- **TB1** ✅ stats.py (ao5/ao12/PB, DNF, JSON) + lazy __init__ · 13 tests pass
- **TB2** ✅ session.py (atomic JSON store + scramble-of-the-day) · +10 tests (23 total)
- **TB3** ✅ test_engine.py (algebraic move properties, importorskip numpy) · whole tree ruff-clean
- **TB4** ⏳ rendering overhaul (animation + materials + HUD)
