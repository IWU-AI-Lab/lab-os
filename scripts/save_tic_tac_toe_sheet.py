"""Save the tic-tac-toe grid as a letter-size PDF to print at 100 % (preview 1;
docs/guides/tic-tac-toe.md). The cells are `board.cell_cm` of config/games/tic-tac-toe.yaml.

    uv run python scripts/save_tic_tac_toe_sheet.py

Writes models/games/tic-tac-toe-sheet-letter.pdf (or --out). Portrait: the bottom edge goes toward
the arm. The grid's near edge is 3 cm from that edge, so with the middle of B2 at the layout's
center_cm, the paper's bottom edge lies (center x − 1.5 cells − 3) cm in front of the base.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lab_os.tools import tic_tac_toe

REPO = Path(__file__).resolve().parents[1]
DPI = 300
PAGE_IN = (8.5, 11.0)
NEAR_EDGE_CM = 3.0  # from the paper's bottom edge (toward the arm) to the grid


def px(cm: float) -> int:
    return round(cm / 2.54 * DPI)


def sheet(cell_cm: float) -> Image.Image:
    w, h = round(PAGE_IN[0] * DPI), round(PAGE_IN[1] * DPI)
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    side = px(cell_cm * 3)
    left, bottom = (w - side) // 2, h - px(NEAR_EDGE_CM)
    top = bottom - side
    thick = px(0.12)
    for k in range(4):  # the grid, outer edge included (the camera sees where the board ends)
        x = left + round(k * side / 3)
        y = top + round(k * side / 3)
        d.line([(x, top), (x, bottom)], fill=0, width=thick)
        d.line([(left, y), (left + side, y)], fill=0, width=thick)
    small = ImageFont.load_default(size=px(0.5))
    for i, row in enumerate(tic_tac_toe.ROWS):
        for j, col in enumerate(tic_tac_toe.COLS):
            x = left + round(j * side / 3) + px(0.35)
            y = top + round(i * side / 3) + px(0.3)
            d.text((x, y), f"{col}{row}", fill=150, font=small)
    cx, cy = left + side // 2, top + side // 2  # a small cross at the middle of B2
    arm = px(0.4)
    d.line([(cx - arm, cy), (cx + arm, cy)], fill=120, width=px(0.04))
    d.line([(cx, cy - arm), (cx, cy + arm)], fill=120, width=px(0.04))
    text = ImageFont.load_default(size=px(0.45))
    notes = [
        (top - px(1.2), f"lab-os tic-tac-toe · cells {cell_cm:g} cm · print at 100 %"),
        (h - px(1.6), "This edge toward the arm"),
    ]
    for y, line in notes:
        d.text((w // 2, y), line, fill=90, font=text, anchor="mm")
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=REPO / "models/games/tic-tac-toe-sheet-letter.pdf")
    args = ap.parse_args()
    game = tic_tac_toe.load()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet(game.cell_cm).save(args.out, "PDF", resolution=DPI)
    edge = game.center_cm[0] - 1.5 * game.cell_cm - NEAR_EDGE_CM
    print(f"Wrote {args.out}. Its bottom edge goes {edge:g} cm in front of the middle of the base.")


if __name__ == "__main__":
    main()
