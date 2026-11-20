"""Camera pixels → table cm for a fixed camera (focus item 6, decision 2026-11-16).

Google's robotics-pointing-sample method (docs/dev/existing-work-teleop-ai.md): a printed ChArUco
board lies flat in front of the arm; one picture of it gives a homography from the picture's
pixels to the table's x/y in cm (the arm's axes: x forward, y to the arm's left, from the middle
of the base). Then `camera_snapshot` draws a cm grid on that camera's pictures, so any AI model
can read off where something is, and `table_point` turns a pixel into cm.

Only right on the table's plane: read the grid where an object touches the table (a 2.5 cm cube's
top looks ~1 cm further away from a camera 60 cm up). The sheet: `models/charuco/` (Google's,
Apache-2.0): 5×7 squares of 35 mm, 26 mm DICT_4X4 markers. Its "board origin" corner (top left,
the first inner corner) is where `origin_cm` is measured to.

OpenCV comes with the `so101` extra; it's imported only where a picture is read or detected.
"""

import io
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

from lab_os import config

SQUARES = (5, 7)  # across, down the sheet
SQUARE_MM = 35.0
MARKER_MM = 26.0
DEFAULT_ORIGIN_CM = (29.0, 5.25)  # the sheet lined up with Google's outline of their arm's plate
MIN_CORNERS = 6
GRID_X_CM = (0, 60)  # where the grid is drawn (cm), every 5 cm, labels every 10
GRID_Y_CM = (-40, 40)


class BoardNotFound(Exception):
    """The picture doesn't show enough of the sheet. The message says what to check."""


@dataclass
class TableMap:
    camera: str
    homography: list[list[float]]  # pixels of a width_px × height_px picture → table cm
    width_px: int
    height_px: int
    origin_cm: tuple[float, float]
    square_mm: float
    corners: int  # how many of the sheet's corners were seen
    worst_mm: float  # the largest miss over those corners (a check of the fit)
    when: str

    def _h(self) -> np.ndarray:
        return np.array(self.homography, dtype=float)

    def to_table(
        self, x_px: float, y_px: float, width_px: int | None = None
    ) -> tuple[float, float]:
        """A pixel of a picture `width_px` wide (default: the calibration's) → table (x, y) cm."""
        k = self.width_px / width_px if width_px else 1.0
        x, y, w = self._h() @ (x_px * k, y_px * k, 1.0)
        if w <= 0:
            raise ValueError("that pixel is above the horizon, not on the table")
        return x / w, y / w

    def to_pixels(self, x_cm: float, y_cm: float, width_px: int | None = None) -> tuple | None:
        """Table (x, y) cm → a pixel of a picture `width_px` wide; None if behind the camera."""
        k = (width_px / self.width_px) if width_px else 1.0
        u, v, w = np.linalg.inv(self._h()) @ (x_cm, y_cm, 1.0)
        if w <= 1e-9:
            return None
        return u / w * k, v / w * k


def _board(square_mm: float):
    import cv2

    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    marker_mm = square_mm * MARKER_MM / SQUARE_MM  # a scaled print scales both
    return cv2.aruco.CharucoBoard(SQUARES, square_mm / 1000, marker_mm / 1000, dictionary)


def board_image(square_px: int = 100, margin_px: int = 0) -> np.ndarray:
    """The sheet's board as a grey image (for tests and for checking a print)."""
    w, h = SQUARES[0] * square_px, SQUARES[1] * square_px
    return _board(SQUARE_MM).generateImage((w + 2 * margin_px, h + 2 * margin_px), None, margin_px)


def calibrate(
    image: np.ndarray,
    camera: str,
    origin_cm: tuple[float, float] = DEFAULT_ORIGIN_CM,
    square_mm: float = SQUARE_MM,
) -> TableMap:
    """Find the sheet in `image` (BGR or grey) and fit pixels → table cm.

    The sheet lies flat with its long edge pointing away from the arm and the "board origin"
    corner at the far left; `origin_cm` is that corner's (x forward, y left) from the middle of the
    arm's base. `square_mm`: one square as printed (35 unless the printer scaled it)."""
    import cv2

    board = _board(square_mm)
    corners, ids, _, _ = cv2.aruco.CharucoDetector(board).detectBoard(image)
    found = 0 if ids is None else len(ids)
    if found < MIN_CORNERS:
        raise BoardNotFound(
            f"saw {found} of the sheet's 24 corners (need {MIN_CORNERS}): is the whole sheet in "
            "the picture, flat, not covered by the arm, and lit evenly (no glare)?"
        )
    local = board.getChessboardCorners()  # metres on the sheet: x across, y down
    o = local[0]
    px, cm = [], []
    for (c,), i in zip(corners, ids.flatten(), strict=True):
        dx, dy = (local[i][0] - o[0]) * 100, (local[i][1] - o[1]) * 100
        px.append(c)
        # down the sheet = toward the arm (−x); across = to the arm's right (−y)
        cm.append((origin_cm[0] - dy, origin_cm[1] - dx))
    px, cm = np.array(px, dtype=float), np.array(cm, dtype=float)
    h, _ = cv2.findHomography(px, cm)
    if h is None:
        raise BoardNotFound("the corners didn't fit a flat sheet: lay it flat and try again")
    fit = cv2.perspectiveTransform(px.reshape(-1, 1, 2), h).reshape(-1, 2)
    worst = float(np.max(np.linalg.norm(fit - cm, axis=1))) * 10
    rows, cols = image.shape[:2]
    return TableMap(
        camera=camera,
        homography=[[float(v) for v in row] for row in h],
        width_px=int(cols),
        height_px=int(rows),
        origin_cm=(float(origin_cm[0]), float(origin_cm[1])),
        square_mm=float(square_mm),
        corners=found,
        worst_mm=round(worst, 1),
        when=datetime.now().isoformat(timespec="seconds"),
    )


# ---------- saving: one file per camera in the place's local/ folder (not in git) ----------


def map_path(camera: str) -> Path:
    return config.local_dir() / "table-maps" / f"{camera}.yaml"


def save(m: TableMap) -> Path:
    path = map_path(m.camera)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(m)
    data["origin_cm"] = list(m.origin_cm)
    head = (
        "# Camera → table cm (lab-os table-map; docs/guides/ai-control.md). Redo it if the camera\n"
    )
    head += "# or the arm moved.\n"
    path.write_text(head + yaml.safe_dump(data, sort_keys=False))
    return path


def load(camera: str) -> TableMap | None:
    """The camera's map, or None if it has none (or the file is broken)."""
    path = map_path(camera)
    if not path.exists():
        return None
    try:
        d = yaml.safe_load(path.read_text())
        d["origin_cm"] = tuple(d["origin_cm"])
        return TableMap(**d)
    except Exception:
        return None


# ---------- the grid on a picture ----------


def _segments(m: TableMap, w: int, h: int, a: tuple, b: tuple, steps: int = 24):
    """Pieces of the table line a→b (cm) as pixel segments inside a w×h picture."""
    out, prev = [], None
    for k in range(steps + 1):
        t = k / steps
        p = m.to_pixels(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, w)
        ok = p is not None and -w < p[0] < 2 * w and -h < p[1] < 2 * h
        if ok and prev is not None:
            out.append((prev, p))
        prev = p if ok else None
    return out


def draw_grid(jpeg: bytes, m: TableMap) -> bytes:
    """`jpeg` with the table's cm grid on it: lines every 5 cm, labels every 10 (x forward, y
    left), a dot at the middle of the arm's base."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    w, h = img.size
    if abs(h / w - m.height_px / m.width_px) > 0.02:
        return jpeg  # another shape than the calibration's: a grid would be wrong
    d = ImageDraw.Draw(img, "RGBA")
    width = max(1, round(w / 640))
    for x in range(GRID_X_CM[0], GRID_X_CM[1] + 1, 5):
        col = (255, 210, 0, 235) if x % 10 == 0 else (255, 210, 0, 120)
        for p, q in _segments(m, w, h, (x, GRID_Y_CM[0]), (x, GRID_Y_CM[1])):
            d.line([p, q], fill=col, width=width * 2 if x % 10 == 0 else width)
    for y in range(GRID_Y_CM[0], GRID_Y_CM[1] + 1, 5):
        col = (0, 200, 255, 235) if y % 10 == 0 else (0, 200, 255, 120)
        for p, q in _segments(m, w, h, (GRID_X_CM[0], y), (GRID_X_CM[1], y)):
            d.line([p, q], fill=col, width=width * 2 if y % 10 == 0 else width)
    font = ImageFont.load_default(size=max(11, round(14 * w / 640)))
    labels = [((x, 0), f"x{x}") for x in range(10, GRID_X_CM[1] + 1, 10)]
    labels += [((20, y), f"y{y:+d}") for y in range(-30, 31, 10) if y]
    for (x, y), text in labels:
        p = m.to_pixels(x, y, w)
        if p and 0 <= p[0] < w - 20 and 0 <= p[1] < h - 10:
            d.text(
                (p[0] + 3, p[1] + 2),
                text,
                fill=(255, 255, 255),
                font=font,
                stroke_width=2,
                stroke_fill=(0, 0, 0),
            )
    base = m.to_pixels(0, 0, w)
    if base and 0 <= base[0] < w and 0 <= base[1] < h:
        r = 4 * width
        d.ellipse([base[0] - r, base[1] - r, base[0] + r, base[1] + r], fill=(255, 60, 60, 220))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def describe(m: TableMap) -> str:
    """One sentence for the AI next to a picture with the grid."""
    return (
        "Table grid in cm from the middle of the arm's base: yellow lines = x (forward), blue = y "
        "(left +, right −), every 5 cm, labelled every 10; red dot = the base. Read an object's "
        "place where it touches the table (its top looks further away). Accurate to ~1 cm."
    )


def fit_ok(m: TableMap) -> bool:
    """A sanity check: the fit's worst corner is within 5 mm."""
    return math.isfinite(m.worst_mm) and m.worst_mm <= 5.0
