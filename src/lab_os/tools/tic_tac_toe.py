"""Tic-tac-toe on a paper grid (preview 1, docs/guides/tic-tac-toe.md): the layout from
config/games/tic-tac-toe.yaml, and the board drawn on the stand camera's picture.

The AI plays with the robot tools it already has: `camera_snapshot(board=true)` shows the board
with each cell labelled and gives the cells' and start spots' positions; `pick_at` takes a piece
from a start spot; `move_to` and `gripper` put it down in a cell. No game logic here: the AI
reads the board and chooses the move.
"""

import io
from dataclasses import dataclass
from pathlib import Path

import yaml

from lab_os import config
from lab_os.tools.table_map import TableMap

FILE = "games/tic-tac-toe.yaml"
ROWS, COLS = "123", "ABC"


class NoGame(Exception):
    """No layout file, or one that can't be read. The message says which file and why."""


@dataclass(frozen=True)
class Layout:
    camera: str
    center_cm: tuple[float, float]
    cell_cm: float
    place_tool_angle_deg: float
    height_cm: float
    robot: str
    person: str
    release_open_pct: float
    robot_start_cm: tuple[tuple[float, float], ...]
    park_cm: tuple[float, float]
    via_cm: tuple[float, float]

    @property
    def travel_z_cm(self) -> float:
        """The height the arm travels at: a held piece clears a standing one by 4.5 cm (it is
        also the height pick_at starts and ends at)."""
        return self.height_cm + 6

    def cells(self) -> dict[str, tuple[float, float]]:
        """ "A1".."C3" → the cell's middle (x, y) cm. Row 1 is far (largest x), column A is on
        the arm's left (largest y)."""
        cx, cy = self.center_cm
        return {
            f"{c}{r}": (cx + (1 - i) * self.cell_cm, cy + (1 - j) * self.cell_cm)
            for i, r in enumerate(ROWS)
            for j, c in enumerate(COLS)
        }

    def summary(self) -> dict:
        """What the AI needs besides the picture."""
        h, z, a = self.height_cm, self.travel_z_cm, self.place_tool_angle_deg
        (px, py), (vx, vy) = self.park_cm, self.via_cm
        park = f"park ({px:g}, {py:g}, {z:g}) with tool_angle_deg 180"
        via = f"via ({vx:g}, {vy:g}, {z:g}) with tool_angle_deg {a:g}"
        return {
            "cells_cm": {k: {"x": x, "y": y} for k, (x, y) in self.cells().items()},
            "cell_cm": self.cell_cm,
            "how_cells_are_named": "row 1 = far from the arm, row 3 = near; column A = the arm's "
            "left, C = its right. In the picture, A1 is at the top left.",
            "robot_colour": self.robot,
            "person_colour": self.person,
            "piece_height_cm": h,
            "robot_start_cm": [
                {"spot": n, "x": x, "y": y} for n, (x, y) in enumerate(self.robot_start_cm, 1)
            ],
            "route": f"The arm waits at {park}: beside its base, so the camera sees the board. "
            f"Every trip goes through {via}. Travel at z {z:g}, and use move_to (at most 10 cm "
            "a call: call again until it arrives). Never go_to_pose ready or home while pieces "
            "are on the board: both poses put the gripper low over the board.",
            "at_the_start": f"With the board still empty: go_to_pose ready, move_to straight up "
            f"to z {z:g}, then via, then park.",
            "to_take_a_piece": f"From park: via, then the point above a start spot that still "
            f"has a {self.robot} piece (z {z:g}, tool_angle_deg 180), then pick_at(x, y, "
            f"height_cm={h:g}). It ends above the spot, holding the piece.",
            "to_put_it_down": f"Via, then above the cell (z {z:g}, tool_angle_deg {a:g}), down "
            f"to z {h / 2 + 0.5:g}, gripper {self.release_open_pct:g}, back up to z {z:g}, via, "
            "park. Then look again.",
            "at_the_end": "When the person has cleared the board: go_to_pose home.",
        }


def path() -> Path:
    return config.shared_path(FILE)


def load(file: Path | None = None) -> Layout:
    file = file or path()
    try:
        raw = yaml.safe_load(file.read_text()) or {}
        board, pieces = raw["board"], raw["pieces"]
        return Layout(
            camera=str(raw["camera"]),
            center_cm=_xy(board["center_cm"]),
            cell_cm=float(board["cell_cm"]),
            place_tool_angle_deg=float(board.get("place_tool_angle_deg", 180)),
            height_cm=float(pieces["height_cm"]),
            robot=str(pieces["robot"]),
            person=str(pieces["person"]),
            release_open_pct=float(pieces.get("release_open_pct", 100)),
            robot_start_cm=tuple(_xy(p) for p in pieces["robot_start_cm"]),
            park_cm=_xy(raw["route"]["park_cm"]),
            via_cm=_xy(raw["route"]["via_cm"]),
        )
    except FileNotFoundError:
        raise NoGame(f"no tic-tac-toe layout: {file} doesn't exist") from None
    except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as e:
        raise NoGame(f"can't read the tic-tac-toe layout {file}: {e}") from None


def _xy(p) -> tuple[float, float]:
    x, y = p
    return float(x), float(y)


def draw(jpeg: bytes, m: TableMap, game: Layout) -> bytes:
    """`jpeg` with the board on it: each cell's outline and name, and each start spot as a
    numbered ring. Unchanged if the picture's shape isn't the table map's."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    w, h = img.size
    if abs(h / w - m.height_px / m.width_px) > 0.02:
        return jpeg
    d = ImageDraw.Draw(img, "RGBA")
    line = max(2, round(2 * w / 640))
    font = ImageFont.load_default(size=max(12, round(16 * w / 640)))
    half = game.cell_cm / 2

    def px(x: float, y: float):
        return m.to_pixels(x, y, w)

    def label(at, text: str) -> None:
        if at and 0 <= at[0] < w and 0 <= at[1] < h:
            d.text(
                at,
                text,
                fill=(255, 255, 255),
                font=font,
                anchor="mm",
                stroke_width=3,
                stroke_fill=(0, 0, 0),
            )

    for name, (x, y) in game.cells().items():
        corners = [px(x + a, y + b) for a, b in ((half, half), (half, -half), (-half, -half))]
        corners.append(px(x - half, y + half))
        if all(corners):
            d.polygon(corners, outline=(255, 0, 255, 230), width=line)
        # the name near the cell's far left corner, so it doesn't hide a piece in the middle
        label(px(x + half * 0.6, y + half * 0.6), name)
    r_cm = 2.0
    for n, (x, y) in enumerate(game.robot_start_cm, 1):
        ring = [px(x + r_cm, y), px(x - r_cm, y)]
        mid = px(x, y)
        if all(ring) and mid:
            r = max(abs(ring[0][1] - ring[1][1]) / 2, 6)
            box = [mid[0] - r, mid[1] - r, mid[0] + r, mid[1] + r]
            d.ellipse(box, outline=(0, 255, 120, 230), width=line)
            label(px(x + r_cm + 1.2, y), str(n))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def describe(game: Layout) -> str:
    """One sentence for the AI next to the picture."""
    return (
        "Magenta squares = the board's cells, each with its name (A1 top left as you look, C3 "
        f"bottom right); green numbered rings = the start spots of the robot's {game.robot} "
        "pieces. A piece is in a cell when its bottom is inside the square (its top looks further "
        "away)."
    )
