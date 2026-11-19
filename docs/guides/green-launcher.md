# The training launcher: so101-green and LeLab in one click

Use it on the lab desktop only. It starts the setup of the SO-101 training project: the green leader and follower, driven from **LeLab** (Hugging Face's web page for LeRobot). It starts nothing until its check says that it is safe.

## Start it
Use one of these:
- **The desktop icon** "SO-101 Training (LeLab)". It is in Ubuntu's app list. To put it in the dock, right-click it and select "Add to Favorites". The icon opens a terminal. The terminal shows the check, then runs LeLab.
- **The Training button in the hub.** It works only on the brain's computer. The page shows the same check. "Start" opens the terminal.
- **A terminal:** in `~/lab-os`, run `uv run lab-os green`.

LeLab then opens http://127.0.0.1:8000 in the browser. Do teleop, recording and training there.

## Stop LeLab
Use one of these:
- Press Ctrl+C in LeLab's terminal.
- Press **Stop LeLab** on the hub's Training page (on the brain's computer). It asks first.
- Run `uv run lab-os green --stop`.

The button and `--stop` stop only the LeLab that the launcher started. The launcher writes that process in `logs/green-lelab.json` and checks that it is still the same LeLab. They leave a LeLab that something else started, and they say so. A recording or a training run in LeLab stops with LeLab.

## LeLab's calibration (since 2026-11-17)
LeLab has one entry, **SO-101_Green**, for both arms. Its calibration files (`lelab_green.json`) are copies of the training files. The training files are the source of truth: `sheep.json` (follower) and `shepherd.json` (leader), from LeRobot's command line. The rules for these files are in `AGENTS.md` → "Hard rules".

To keep the training files safe:
- On LeLab's calibration page, never use the names `sheep` or `shepherd`.
- On the command line, at "Press ENTER to use provided calibration file … or type 'c'", press ENTER. Never type `c`.

The old LeLab entries and their files are in `~/green-calibration-backup/old-lelab/`. A backup of everything from before the change is in `~/green-calibration-backup/before-2026-11-17/`. `scripts/green-lelab-from-training.sh` made the change.

## The check
The launcher starts nothing unless every line is correct:
1. **Both green arms are plugged in** (`…1599` and `…3501` in `/dev/serial/by-id/`).
2. **No other device is on a serial port**, especially not the white arm. LeLab saves its ports as `/dev/ttyACM0` and `ttyACM1`, and Linux gives those numbers in plug-in order. With the white arm plugged in, LeLab's "leader" can be the white arm (this happened on 2026-11-10).
3. **LeLab's saved ports are the two green arms**, one leader and one follower. The launcher reads `~/.cache/huggingface/lerobot/ports/*.txt` and `robots/*.json`. It never changes them.
4. **The arms are the same way round as at the last good start.** `logs/green-last-start.json` keeps which serial was the follower. If you plug the arms in again in the other order, the leader and the follower swap. Then the launcher refuses. Unplug both arms and plug in the follower first, or select the ports again in LeLab.
5. **No other program has a green port open**, for example `lab-os serve --arm so101-green`. The launcher names the program. Stop it first (for the brain: Ctrl+C in its terminal). Only LeLab may already have the ports. The launcher knows LeLab by its command line, and it does this check also when LeLab is not running (since 2026-11-17, quick job 17).

If a line fails, the launcher says what to change and opens nothing. After the first good start, move the leader once in LeLab and make sure that the follower moves.

## What the launcher never does
- It never opens a green port. It only reads the names in `/dev/serial/by-id/` and, from `/proc`, which programs have them open.
- It never changes LeLab's settings, the calibration folder or the `lerobot` conda environment.

LeLab is its own uv tool (`~/.local/share/uv/tools/lelab`, with its own LeRobot). The launcher starts it as it is. lab-os itself may drive the green follower (`docs/guides/ai-control.md` → "The green arm"), but never at the same time as LeLab. The code is in `src/lab_os/green.py`.

## Move the icon to another computer
The icon is the file `~/.local/share/applications/lab-os-training.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=SO-101 Training (LeLab)
Exec=gnome-terminal --title "SO-101 training (LeLab)" -- /home/<user>/lab-os/.venv/bin/lab-os green --wait
Path=/home/<user>/lab-os
Icon=applications-science
Categories=Science;
```
