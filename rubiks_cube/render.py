"""3D rendering helpers for the Rubik's cube (matplotlib).

Separated from the interactive app loop so the geometry/animation math can be
reasoned about (and partially tested) independently of the event handling.

This module imports numpy and matplotlib lazily inside functions so that merely
importing :mod:`rubiks_cube.render` does not fail in environments without those
libraries; only actually rendering does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Face index constants (mirror of cube_state's U,D,L,R,F,B). Defined locally so
# importing this module does not pull in numpy via cube_state; the engine still
# owns the canonical definitions and they are asserted equal in tests.
U, D, L, R, F, B = 0, 1, 2, 3, 4, 5

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np
    from numpy.typing import NDArray

    from .cube_state import CubeState

# Standard "speedcube" palette (slightly desaturated for a nicer look than pure
# primaries). face index -> hex color.
COLOR_MAP: dict[int, str] = {
    U: "#F2F2F2",  # White  (Up)
    D: "#FFD500",  # Yellow (Down)
    L: "#009E3B",  # Green  (Left)
    R: "#2160D4",  # Blue   (Right)
    F: "#C8102E",  # Red    (Front)
    B: "#FF6D00",  # Orange (Back)
}

_PLASTIC = "#15171A"  # cube body / gaps color
_GAP = 0.08  # gap between facelets (fraction of a unit cell)

# Which axis each face's turn rotates about, and the sign of a clockwise
# (looking from outside) turn. Used for animating a face rotation.
#   axis: 0=x, 1=y, 2=z
_FACE_AXIS: dict[int, int] = {U: 1, D: 1, L: 0, R: 0, F: 2, B: 2}
_FACE_CW_SIGN: dict[int, float] = {U: -1.0, D: 1.0, L: 1.0, R: -1.0, F: -1.0, B: 1.0}
# Plane coordinate (on the rotation axis) of the moving layer's outer face.
_FACE_LAYER_COORD: dict[int, float] = {U: 1.5, D: -1.5, L: -1.5, R: 1.5, F: 1.5, B: -1.5}


def facelet_vertices(face: int, row: int, col: int) -> NDArray[np.float64]:
    """Return the 4 corner vertices (as a 4x3 array) of one facelet.

    The cube spans (-1.5, -1.5, -1.5) to (1.5, 1.5, 1.5). ``row``/``col`` index
    into the 3x3 grid of a face using the same convention as
    :class:`~rubiks_cube.cube_state.CubeState`.
    """
    import numpy as np

    lo, hi = _GAP, 1.0 - _GAP

    if face == U:  # y = 1.5 plane
        x0, x1 = -1.5 + col + lo, -1.5 + col + hi
        z0, z1 = -1.5 + (2 - row) + lo, -1.5 + (2 - row) + hi
        v = [[x0, 1.5, z0], [x1, 1.5, z0], [x1, 1.5, z1], [x0, 1.5, z1]]
    elif face == D:  # y = -1.5 plane
        x0, x1 = -1.5 + col + lo, -1.5 + col + hi
        z0, z1 = -1.5 + row + lo, -1.5 + row + hi
        v = [[x0, -1.5, z0], [x1, -1.5, z0], [x1, -1.5, z1], [x0, -1.5, z1]]
    elif face == F:  # z = 1.5 plane
        x0, x1 = -1.5 + col + lo, -1.5 + col + hi
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        v = [[x0, y0, 1.5], [x1, y0, 1.5], [x1, y1, 1.5], [x0, y1, 1.5]]
    elif face == B:  # z = -1.5 plane (mirrored)
        x0, x1 = 1.5 - (col + hi), 1.5 - (col + lo)
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        v = [[x0, y0, -1.5], [x1, y0, -1.5], [x1, y1, -1.5], [x0, y1, -1.5]]
    elif face == R:  # x = 1.5 plane
        z0, z1 = 1.5 - (col + hi), 1.5 - (col + lo)
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        v = [[1.5, y0, z0], [1.5, y0, z1], [1.5, y1, z1], [1.5, y1, z0]]
    elif face == L:  # x = -1.5 plane
        z0, z1 = -1.5 + col + lo, -1.5 + col + hi
        y0, y1 = 1.5 - (row + hi), 1.5 - (row + lo)
        v = [[-1.5, y0, z0], [-1.5, y0, z1], [-1.5, y1, z1], [-1.5, y1, z0]]
    else:
        raise ValueError(f"Invalid face: {face}")

    return np.array(v, dtype=np.float64)


def rotation_matrix(axis: int, angle_rad: float) -> NDArray[np.float64]:
    """Return a 3x3 rotation matrix about x(0), y(1), or z(2) by ``angle_rad``."""
    import numpy as np

    c, s = np.cos(angle_rad), np.sin(angle_rad)
    if axis == 0:
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)
    if axis == 1:
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)
    if axis == 2:
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)
    raise ValueError(f"axis must be 0, 1 or 2, got {axis}")


def _facelet_belongs_to_layer(verts: NDArray[np.float64], face_turned: int) -> bool:
    """True if a facelet (given its vertices) is part of the turning layer.

    A facelet moves with a face turn if all of its vertices lie on the outer
    side of the rotation axis for that face (within a tolerance).
    """
    axis = _FACE_AXIS[face_turned]
    coord = _FACE_LAYER_COORD[face_turned]
    comp = verts[:, axis]
    if coord > 0:
        return bool((comp >= coord - 1.0 - 1e-6).all())
    return bool((comp <= coord + 1.0 + 1e-6).all())


class CubeRenderer:
    """Draws a :class:`CubeState` on a matplotlib 3D axis, with animation.

    Parameters
    ----------
    ax : matplotlib 3D axis
        The axis to draw on.
    """

    def __init__(self, ax: Any) -> None:
        self.ax = ax
        self._elev = 28.0
        self._azim = -52.0

    def _collect_facelets(
        self, state: CubeState
    ) -> tuple[list[NDArray[np.float64]], list[str]]:
        verts: list[NDArray[np.float64]] = []
        colors: list[str] = []
        for face in range(6):
            for row in range(3):
                for col in range(3):
                    verts.append(facelet_vertices(face, row, col))
                    colors.append(COLOR_MAP[int(state.facelets[face, row, col])])
        return verts, colors

    def _apply_axes_style(self) -> None:
        self.ax.set_xlim(-2, 2)
        self.ax.set_ylim(-2, 2)
        self.ax.set_zlim(-2, 2)
        self.ax.set_box_aspect([1, 1, 1])
        self.ax.set_axis_off()
        self.ax.view_init(elev=self._elev, azim=self._azim)

    def draw(self, state: CubeState) -> None:
        """Render the static cube in its current state."""
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        self.ax.cla()
        verts, colors = self._collect_facelets(state)
        collection = Poly3DCollection(
            verts,
            facecolors=colors,
            edgecolors=_PLASTIC,
            linewidths=1.4,
        )
        collection.set_zsort("average")
        self.ax.add_collection3d(collection)
        self._apply_axes_style()

    def draw_mid_turn(
        self, state: CubeState, face_turned: int, angle_rad: float
    ) -> None:
        """Render the cube with the turning layer rotated by ``angle_rad``.

        ``state`` is the cube *before* the turn is logically applied; the layer
        belonging to ``face_turned`` is drawn rotated by the partial angle so a
        sequence of calls with increasing angle animates the turn.
        """
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        self.ax.cla()
        verts, colors = self._collect_facelets(state)
        axis = _FACE_AXIS[face_turned]
        rot = rotation_matrix(axis, angle_rad)

        rendered: list[NDArray[np.float64]] = []
        for v in verts:
            if _facelet_belongs_to_layer(v, face_turned):
                rendered.append((rot @ v.T).T)
            else:
                rendered.append(v)

        collection = Poly3DCollection(
            rendered,
            facecolors=colors,
            edgecolors=_PLASTIC,
            linewidths=1.4,
        )
        collection.set_zsort("average")
        self.ax.add_collection3d(collection)
        self._apply_axes_style()

    @staticmethod
    def turn_angle(face_turned: int, quarter_turns: int, t: float) -> float:
        """Interpolated angle (radians) for an animation frame.

        Parameters
        ----------
        face_turned : int
            Face index being turned.
        quarter_turns : int
            1 for a CW quarter turn, -1 for CCW, 2 for a half turn.
        t : float
            Animation progress in [0, 1].
        """
        import numpy as np

        total = _FACE_CW_SIGN[face_turned] * (np.pi / 2.0) * quarter_turns
        return total * t
