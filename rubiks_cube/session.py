"""Practice-session persistence and daily scrambles.

Pure-Python (no numpy) so it runs and tests anywhere. Provides:

- :class:`SessionStore` — load/save :class:`~rubiks_cube.stats.SolveStats`
  to a JSON file (default ``~/.rubiks_cube/stats.json``), with atomic writes.
- :func:`scramble_of_the_day` — a deterministic scramble seeded by the date,
  so the same day always yields the same scramble (great for daily practice).
"""

from __future__ import annotations

import contextlib
import json
import os
import random
import tempfile
from datetime import date
from pathlib import Path

from .stats import SolveStats

_DEFAULT_DIR = Path.home() / ".rubiks_cube"
_DEFAULT_FILE = _DEFAULT_DIR / "stats.json"

# Faces and their modifiers, used for dependency-free scramble generation.
_FACES = ["U", "D", "L", "R", "F", "B"]
_MODIFIERS = ["", "'", "2"]


class SessionStore:
    """Persists a :class:`SolveStats` history to a JSON file.

    Parameters
    ----------
    path : str | os.PathLike | None
        Target JSON file. Defaults to ``~/.rubiks_cube/stats.json``.

    Examples
    --------
    >>> import tempfile, os
    >>> from rubiks_cube.stats import Solve
    >>> d = tempfile.mkdtemp()
    >>> store = SessionStore(os.path.join(d, "stats.json"))
    >>> stats = store.load()          # empty on first use
    >>> stats.add(Solve(time=12.0))
    >>> store.save(stats)
    >>> store.load().count
    1
    """

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path) if path is not None else _DEFAULT_FILE

    def load(self) -> SolveStats:
        """Load stats from disk, returning an empty history if absent/corrupt."""
        if not self.path.exists():
            return SolveStats()
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable file: start fresh rather than crash.
            return SolveStats()
        if not isinstance(data, dict):
            return SolveStats()
        return SolveStats.from_dict(data)

    def save(self, stats: SolveStats) -> None:
        """Atomically write stats to disk, creating parent dirs as needed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file in the same dir, then atomically replace, so a
        # crash mid-write can never corrupt the existing stats file.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=".stats-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(stats.to_dict(), fh, indent=2)
            os.replace(tmp_name, self.path)
        except BaseException:
            # Clean up the temp file on any failure.
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise


def _scramble_from_rng(rng: random.Random, length: int = 20) -> str:
    """Generate a WCA-style scramble string using the given RNG.

    No two consecutive moves use the same face. Dependency-free (does not
    import the numpy-backed engine), returning plain notation text.
    """
    moves: list[str] = []
    last_face: str | None = None
    for _ in range(length):
        choices = [f for f in _FACES if f != last_face]
        face = rng.choice(choices)
        modifier = rng.choice(_MODIFIERS)
        moves.append(face + modifier)
        last_face = face
    return " ".join(moves)


def scramble_of_the_day(on: date | None = None, length: int = 20) -> str:
    """Return a deterministic scramble for a given date.

    The same date always produces the same scramble, so a "daily scramble"
    is reproducible across machines and sessions.

    Parameters
    ----------
    on : datetime.date | None
        The date to seed from. Defaults to today.
    length : int
        Number of moves in the scramble.

    Returns
    -------
    str
        Scramble in standard notation, e.g. ``"U R' F2 D ..."``.

    Examples
    --------
    >>> from datetime import date
    >>> a = scramble_of_the_day(date(2026, 1, 1))
    >>> b = scramble_of_the_day(date(2026, 1, 1))
    >>> a == b
    True
    """
    day = on or date.today()
    seed = day.toordinal()
    rng = random.Random(seed)
    return _scramble_from_rng(rng, length=length)
