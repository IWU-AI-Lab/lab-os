# The table-map sheet (ChArUco board)

Printed and laid in front of an arm, it lets `lab-os table-map <camera>` learn how a fixed camera's pixels map to table cm (`docs/guides/ai-control.md` → "Table map"; `src/lab_os/tools/table_map.py`).

| | |
|---|---|
| Source | [google-gemini/robotics-pointing-sample](https://github.com/google-gemini/robotics-pointing-sample), `media/calibration_sheet_letter.pdf` |
| Commit | shallow clone of `main`, downloaded 2026-11-16 (last change 2026-02-12) |
| License | Apache-2.0 (`LICENSE`, copied from that repository) |
| Files | `calibration-sheet-letter.pdf`, unmodified (renamed). A4 and legal versions are in the source |

The board: 5 × 7 squares of 35 mm, 26 mm markers, OpenCV's `DICT_4X4_250`. **Print at 100 % ("Actual size", not "Fit to page")**, then measure one square: if it isn't 35 mm, pass `--square-mm` with what you measured. Its "Board origin" corner (top left, labelled on the sheet) is where `--origin` is measured to. The arm outline at the bottom is Google's mounting plate, not ours: ignore it and measure.
