"""Rubik's cube state representation.

The cube state is stored as a (6, 3, 3) NumPy array of int8 values where each
element represents the color index (0-5) of a single facelet.

Face ordering:
    U=0, D=1, L=2, R=3, F=4, B=5
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# Face index constants
U, D, L, R, F, B = 0, 1, 2, 3, 4, 5

# Kociemba face order mapping: U R F D L B
_KOCIEMBA_FACE_ORDER = [U, R, F, D, L, B]
_KOCIEMBA_FACE_CHARS = "URFDLB"


class CubeState:
    """Immutable Rubik's cube state.

    Parameters
    ----------
    facelets : NDArray[np.int8]
        Shape (6, 3, 3) array of face color indices (0-5).
        Face ordering: U=0, D=1, L=2, R=3, F=4, B=5.

    Examples
    --------
    >>> cube = CubeState.solved()
    >>> cube.is_solved()
    True
    >>> cube.facelets.shape
    (6, 3, 3)
    """

    __slots__ = ("_facelets", "_hash")

    def __init__(self, facelets: NDArray[np.int8]) -> None:
        if facelets.shape != (6, 3, 3):
            raise ValueError(
                f"facelets must have shape (6, 3, 3), got {facelets.shape}"
            )
        # Store as immutable (read-only) array
        facelets = facelets.copy()
        facelets.flags.writeable = False
        self._facelets = facelets
        self._hash: int | None = None

    @property
    def facelets(self) -> NDArray[np.int8]:
        """The (6, 3, 3) facelet array (read-only)."""
        return self._facelets

    @classmethod
    def solved(cls) -> CubeState:
        """Create a solved cube where face i has all facelets set to i.

        Returns
        -------
        CubeState
            A cube in the solved configuration.

        Examples
        --------
        >>> CubeState.solved().facelets[0, 1, 1]
        0
        """
        facelets = np.zeros((6, 3, 3), dtype=np.int8)
        for i in range(6):
            facelets[i] = i
        return cls(facelets=facelets)

    def is_solved(self) -> bool:
        """Check if the cube is in the solved state.

        Returns
        -------
        bool
            True if every face has uniform color matching its index.

        Examples
        --------
        >>> CubeState.solved().is_solved()
        True
        """
        for i in range(6):
            if not np.all(self._facelets[i] == i):
                return False
        return True

    def to_kociemba_string(self) -> str:
        """Convert to 54-character string for Kociemba solver input.

        The string is ordered U R F D L B, reading each face left-to-right,
        top-to-bottom. Each character is one of 'U', 'R', 'F', 'D', 'L', 'B'
        indicating which face's color that facelet shows.

        Returns
        -------
        str
            54-character string representation.

        Examples
        --------
        >>> CubeState.solved().to_kociemba_string()
        'UUUUUUUUURRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
        """
        chars: list[str] = []
        for face_idx in _KOCIEMBA_FACE_ORDER:
            face = self._facelets[face_idx]
            for row in range(3):
                for col in range(3):
                    color = int(face[row, col])
                    # Map internal color index to Kociemba face character
                    chars.append(_KOCIEMBA_FACE_CHARS[_KOCIEMBA_FACE_ORDER.index(color)])
        return "".join(chars)

    # Keep backward-compatible alias
    to_string = to_kociemba_string

    @classmethod
    def from_kociemba_string(cls, s: str) -> "CubeState":
        """Parse a 54-character Kociemba string back into a CubeState.

        The string must be ordered U R F D L B, with each character being
        one of 'U', 'R', 'F', 'D', 'L', 'B'.

        Parameters
        ----------
        s : str
            54-character Kociemba format string.

        Returns
        -------
        CubeState
            The parsed cube state.

        Raises
        ------
        ValueError
            If the string length is not 54 or contains invalid characters.

        Examples
        --------
        >>> cube = CubeState.from_kociemba_string(
        ...     'UUUUUUUUURRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
        ... )
        >>> cube.is_solved()
        True
        """
        if len(s) != 54:
            raise ValueError(
                f"Kociemba string must be exactly 54 characters, got {len(s)}"
            )

        # Build reverse mapping: character -> internal color index
        char_to_color: dict[str, int] = {}
        for i, face_idx in enumerate(_KOCIEMBA_FACE_ORDER):
            char_to_color[_KOCIEMBA_FACE_CHARS[i]] = face_idx

        facelets = np.zeros((6, 3, 3), dtype=np.int8)
        idx = 0
        for face_idx in _KOCIEMBA_FACE_ORDER:
            for row in range(3):
                for col in range(3):
                    ch = s[idx]
                    if ch not in char_to_color:
                        raise ValueError(
                            f"Invalid character '{ch}' at position {idx}. "
                            f"Expected one of: {_KOCIEMBA_FACE_CHARS}"
                        )
                    facelets[face_idx, row, col] = char_to_color[ch]
                    idx += 1
        return cls(facelets=facelets)

    def __eq__(self, other: object) -> bool:
        """Check equality with another CubeState."""
        if not isinstance(other, CubeState):
            return NotImplemented
        return np.array_equal(self._facelets, other._facelets)

    def __hash__(self) -> int:
        """Hash the cube state for use in sets and dicts."""
        if self._hash is None:
            self._hash = hash(self._facelets.tobytes())
        return self._hash

    def __repr__(self) -> str:
        """Return string representation."""
        return f"CubeState(solved={self.is_solved()})"
