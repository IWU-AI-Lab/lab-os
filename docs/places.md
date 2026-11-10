# Places: running lab-os somewhere other than the lab

lab-os keeps nothing about a particular place in its code (current-focus.md, rule 9). A **place** is wherever a brain runs: the AI lab, the builder's home, someone else's lab. Everything about it lives in one **config folder**.

The repo's own `config/` is the **lab's** place. Another place gets its own folder, **outside the repo**, with its own `.env`.

## Start a new place
```bash
uv run lab-os new-place ~/my-lab-os                 # writes a starter (never overwrites)
uv run lab-os serve --config ~/my-lab-os            # the hub, with this place's name and devices
uv run lab-os-teleop --config ~/my-lab-os serve     # same option for teleop on its own
```
Or set `LAB_OS_CONFIG=~/my-lab-os` in your shell and leave out `--config`.

The starter has:
| File | What |
|---|---|
| `place.yaml` | `name` (the hub's title and the startup title), `venue` (the default venue), `domain` (planned, step 7) |
| `devices.yaml` | the devices here; starts with the software arm only |
| `venues/home.yaml` | how cautious to be here (speed, motion allowed, active devices) |
| `.env.example` | copy to `.env` in the same folder (your place's folder, not lab-os's `src/lab_os/place_template/`) and put your own API keys in it |

## Which file comes from where
- **Place files** are only ever read from the place's own folder: `place.yaml`, `devices.yaml`, `venues/`. A home brain never borrows the lab's name, devices or venues. If one is missing, lab-os stops and says so.
- **Shared files** are read from the place's folder if it has them, else from the repo's `config/`: `theme.yaml` (one design everywhere), `poses.yaml` (per arm model), and from steps 4–5 `models.yaml` and `personas/`.
- **`.env`**: the place's own `<folder>/.env`. For the repo's `config/` it's the repo's `.env` (the top folder, next to `pyproject.toml`). Variables already set in the shell win over the file. If the file isn't there, `lab-os serve` logs `no …/.env: no API keys` with the exact path it looked for. `new-place` never copies a `.env`, so keys never spread to a new place.
- **The lab's off-limits devices** (`so101-green`, the training cameras in the repo's `config/devices.yaml`) are refused **at every place**, even if another folder's `devices.yaml` lists them differently. Switching folders can never make them openable.

## Your own arm
Add it to your `devices.yaml` (by `/dev/serial/by-id/…` path and USB serial, like the lab's), add its name to your venue's `active_devices`, then `lab-os serve --config ~/my-lab-os --arm <its name>`. `--arm` accepts `fake`, `fake-xarm1` or any SO-101 (`kind: so101`) or xArm (`kind: xarm1s`) in the place's device list. Calibration files go to the repo's `calibration/<arm name>/` (one folder per arm, so a home arm with its own name never touches the lab's).
