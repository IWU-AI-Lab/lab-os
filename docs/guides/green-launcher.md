# The training launcher: so101-green + LeLab in one click

On the lab desktop only. Starts the SO-101 training project's setup (the green leader and follower,
driven from **LeLab**, Hugging Face's web page for LeRobot) after checking that it's safe.

## How to start it
- **The desktop icon** "SO-101 Training (LeLab)" (Ubuntu's app list; right-click → Add to Favorites puts it in the dock). It opens a terminal that shows the check, then runs LeLab there (Ctrl+C stops it).
- **Stopping LeLab** (since 2026-11-16): Ctrl+C in its terminal, **Stop LeLab** on the hub's Training page (on the brain's computer, with a confirmation), or `uv run lab-os green --stop`. The button and `--stop` stop only the LeLab the launcher started (it notes the process in `logs/green-lelab.json` and checks it's still that same LeLab), the way Ctrl+C does; a LeLab started some other way is left alone and they say so. A recording or training run in LeLab stops with it.
- **The hub's Training button** (on the brain's computer only): the same check on the page; Start opens that terminal.
- **A terminal:** `uv run lab-os green` in `~/lab-os`.

LeLab then opens **http://127.0.0.1:8000** in the browser. Teleop, recording and training happen there, as before.

## The check (nothing starts unless every line is fine)
1. **Both green arms are plugged in** (`…1599` and `…3501` in `/dev/serial/by-id/`).
2. **Nothing else is on a serial port**, the white arm above all. LeLab saves its ports as raw `/dev/ttyACM0` / `ttyACM1`, and Linux hands those numbers out in plug-in order: with the white arm plugged in, LeLab's "leader" can be the white arm (on 2026-11-10 it was: white = `ttyACM0` = LeLab's leader).
3. **LeLab's saved ports are exactly the two green arms**, one leader and one follower (`~/.cache/huggingface/lerobot/ports/*.txt` and `robots/*.json`, read only).
4. **Same way round as at the last good start** (`logs/green-last-start.json` remembers which serial was the follower). After a re-plug in the other order, leader and follower would swap: it refuses, and says to unplug both and plug the follower in first (or pick the ports again in LeLab).
5. **No other program has a green port open** (since step 11: e.g. `lab-os serve --arm so101-green` still running). It names the program; stop it first. Skipped when LeLab is already running (then the ports are LeLab's).

If a line fails, it says what to change and opens nothing. The first good start remembers the pairing: check once in LeLab that the follower really moves when you move the leader.

## What it never does
Open a green port (it only reads the names in `/dev/serial/by-id/` and which programs have them open, from `/proc`), change LeLab's settings, touch the calibration folder or the `lerobot` conda env. (lab-os itself may drive the green follower since step 11, `docs/guides/ai-control.md` → "The green arm"; the brain and LeLab never at the same time.) LeLab is its own uv tool (`~/.local/share/uv/tools/lelab`, with its own LeRobot), started as is. The code: `src/lab_os/green.py`.

## Moving the icon to another computer
It's `~/.local/share/applications/lab-os-training.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=SO-101 Training (LeLab)
Exec=gnome-terminal --title "SO-101 training (LeLab)" -- /home/<user>/lab-os/.venv/bin/lab-os green --wait
Path=/home/<user>/lab-os
Icon=applications-science
Categories=Science;
```
