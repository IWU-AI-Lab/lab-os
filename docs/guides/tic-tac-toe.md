# Tic-tac-toe: the robot plays against you

Claude Code plays tic-tac-toe with `so101-white` against a person. The board is a printed grid on letter paper, and the pieces are LEGO bricks. The AI looks at the board through the stand camera, chooses its move, and puts its piece down with the arm. It uses the brain's usual robot tools (`docs/guides/ai-control.md`), so the same limits and STOP apply. This is preview 1 of the demo (`docs/plan/current-focus.md`, item 7).

The lab plays with Claude Code (decision 2026-11-20: no Codex or Gemini CLI in the lab). If one model plays badly, type `/model` and try another.

## What you need
- The grid: print `models/games/tic-tac-toe-sheet-letter.pdf` at **100 %** ("Actual size", not "Fit to page").
- 5 red pieces for the robot and 5 blue pieces for the person. A piece is a Duplo 2×2 brick, or three normal 2×2 bricks pressed together (about 3 cm tall).
- `so101-white` with its stand camera, and the stand camera's table map (`docs/guides/ai-control.md` → "Table map").
- Claude Code on the lab desktop.

The layout is in `config/games/tic-tac-toe.yaml`: where the board is, the size of a cell, where the robot's pieces stand, the colours, and the route of the arm. The brain reads the file each time, so a change needs no restart. To print the sheet again with another cell size, change `cell_cm` and run `uv run python scripts/save_tic_tac_toe_sheet.py`.

## 1. Set up the table
1. Clear the table in front of the arm.
2. Check the print: one cell is as wide as two cubes (6 cm).
3. Put the sheet flat in front of the arm, with the edge marked "This edge toward the arm" toward the arm.
4. Put that edge 12 cm (four cube lengths) in front of the middle of the arm's base. Put the cross in cell B2 straight in front of the base.
5. Put the 5 red pieces at their start spots: three on the arm's left and two on its right, about 16 cm to the side of the base. Step 4 below shows the exact spots as green rings.
6. Keep the 5 blue pieces next to you.
7. If the camera or the arm moved since the last table map, make the table map again (`docs/guides/ai-control.md` → "Table map").

## 2. Start the brain
For the real arm, run:
```bash
uv run --extra so101 lab-os serve --arm so101-white --speed 0.3
```
Open **http://localhost:8080/ai** (AI Control) on the desktop to see each call. Keep one hand near STOP.

To try the game without the arm, run `uv run lab-os serve` (the fake arm). The fake arm has no camera, so you tell the AI where your pieces are.

## 3. Connect Claude Code (one time for each computer)
Start the brain first. Then follow `docs/guides/ai-control.md`, section 2. Claude Code moves the arm without asking (section 3 there). The brain's limits and STOP apply.

## 4. Check the board in the picture
Type this in Claude Code:
> Use the lab-os tools. Take a camera_snapshot of so101-white-cam-stand with board true, and show me the picture.

The picture shows the board's cells as magenta squares, each with its name (A1 at the top left), and the robot's start spots as green numbered rings.
- If the magenta squares are not on the printed lines, move the paper until they are. Take the picture again.
- If a red piece is not in its green ring, move the piece.

## 5. Play
Copy this prompt into Claude Code:
> Let's play tic-tac-toe with the lab-os tools. You play red with the robot arm, and I play blue. Take a camera_snapshot of so101-white-cam-stand with board true. Follow the "board" part of its result exactly: the route, how to take a piece, and how to put it down. Do "at_the_start" first. I go first. When I say "your turn", look again, write the board as a 3×3 grid, choose your move, and say it in one line. Then make it. After each move, say if someone won or if it is a draw. Move slowly. I have STOP in reach.

Put your blue piece in a cell, then say "your turn". On the fake arm, say the cell too ("I put mine on B2, your turn").

When the game ends, clear the board. Then tell the AI to go home.

## How the robot takes a turn
The AI gets these steps from the brain (in the result of `camera_snapshot` with board true). The numbers come from `config/games/tic-tac-toe.yaml`.
- **The route:** the arm waits at a park point beside its base, so the camera sees the whole board. Every trip goes through one point above the board's near edge. The arm moves 9 cm above the table (the piece's height + 6 cm), so a held piece clears a standing piece.
- **Take a piece:** from the park point, through the route point, to above a start spot, then `pick_at` (open, down, close, lift).
- **Put it down:** through the route point, to above the cell, tilted 15° from straight down, down to 2 cm, open the gripper to 60 %, back up, through the route point, back to the park point.
- **Not used during the game:** the `ready` and `home` poses. Both put the gripper low over the board (on the arm's 3D model, `home` is 19 cm in front of the base and 1.6 cm high). The AI goes to `ready` only at the start, with the board empty, and to `home` only at the end, after the board is cleared.

Why these numbers (tested on the fake arm, `tests/test_tic_tac_toe.py`): pointing straight down, `pick_at` reaches only about 14 to 19 cm to the side of the base. So the start spots are there. Tilted 15°, the arm reaches every cell. The gripper opens to 60 % only, because fully open jaws can hit a piece in the next cell.

## If something goes wrong
- **The arm goes the wrong way:** press STOP. The AI is told not to move again until you say so.
- **A pick missed** (`"result": "missed"`): tell the AI to look again before it tries again.
- **The AI reads the board wrong:** tell it the board in words ("A1 blue, B2 red").
- **The AI goes to `ready` or `home` during the game:** press STOP, and remind it of the route.
