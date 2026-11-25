# Places: running lab-os somewhere other than the lab

lab-os keeps nothing about a particular place in its code (docs/plan/current-focus.md, rule 9). A **place** is wherever a brain runs: the AI lab, the builder's home, someone else's lab. Everything about it lives in one **config folder**.

The repo's own `config/` is the **lab's** place. Another place gets its own folder, **outside the repo**, with its own `.env`.

## The place's own changes: `local/`
The files in a config folder are the **defaults**. What a place changes itself goes into its **`local/`** folder: `config/local/` in the lab, `~/my-lab-os/local/` at another place. Git ignores `config/local/`.
- **The settings page writes there, and only the value that changed.** For example, the persona changed to Jarvis gives `local/place.yaml` with `persona: jarvis`, and the lab's speed cap switched off gives `local/venues/lab.yaml` with `limits: {speed_cap: false}`.
- **The brain merges the files, value by value:** first the repo's `config/` (for a shared file), then the place's own file, then `local/`. The later file wins. A section (`hub:`, `limits:`) merges key by key. A single value or a list (`hub.modules`) is replaced as a whole.
- **So a new field in the repo reaches every place.** A place that changed other values in the same file keeps its changes.
- **To go back to the default,** delete the line in the `local/` file (or delete the file). A `local/` file keeps its comments when the page changes a value.
- **Also in `local/`:** `hub-devices.yaml` (each device's settings, "Devices" below) and `table-maps/` (`docs/guides/ai-control.md`).
- **To change a default for every place,** edit the file in `config/` and commit it.

Since 2026-11-20. Before, the settings page wrote into the files in `config/` (the lab's changes showed in `git diff config/`), and a place got a full copy of `theme.yaml` on its first change. That copy did not get new fields. A full copy still works: it is merged like any other layer.

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
| `place.yaml` | `name` (the hub's title and the startup title), `venue` (the default venue), `persona` (who the assistant is, `docs/dev/personas.md`), `ai_budget_usd_month`, `chat_keep_minutes` (`docs/dev/chat.md`), `assistant_moves_arm` (the hub's assistant may move the arm, off by default: `docs/archive/guides-2026-11-25/hub.md`), `drive_from` (other devices that may drive a real arm, by name or address: `docs/archive/guides-2026-11-25/hub.md`), `domain` (not used yet: the secure address is deferred, `docs/plan/current-focus.md` → step 7) |
| `devices.yaml` | the devices here; starts with the software arm only |
| `venues/home.yaml` | how cautious to be here (speed, motion allowed, active devices) |
| `.env.example` | copy to `.env` in the same folder (your place's folder, not lab-os's `src/lab_os/place_template/`) and put your own API keys in it |

`place.yaml` may also say what the place is, in a few words (`about: "a lab where students build robots"`): the visitors' welcome uses it ("Welcome to the AI Comp Lab, a lab where …"; `docs/archive/guides-2026-11-25/hub.md` → "Visitor mode"). A venue with `visitors: true` is the one visitor mode switches to ("hey Jarvis, it's demo time", or ⚙ → Visitor mode); its `try_this:` lists the hub's cards then. A fixed move like the wave is in `gestures.yaml` (shared, like `poses.yaml`).

## Which file comes from where
- **Place files** are only ever read from the place's own folder (and its `local/`): `place.yaml`, `devices.yaml`, `venues/`, `room.yaml` (which device shows which page, quick job 71; a place without one gets "the room's layout is empty"). A home brain never borrows the lab's name, devices or venues. If one is missing, lab-os stops and says so.
- **`local/hub-devices.yaml`** (since step 8) is written by the hub itself: each device's own settings by name (⚙ → This device; `docs/archive/guides-2026-11-25/hub.md` → "Devices"). It appears on the first change; a place without one starts with every device at the defaults.
- **Shared files** come from the repo's `config/`. `theme.yaml` merges the place's own `theme.yaml` and `local/theme.yaml` over the repo's (above). `poses.yaml` (per arm model), `models.yaml` and `personas/`: the place's own file replaces the repo's.
- **`.env`**: the place's own `<folder>/.env`. For the repo's `config/` it's the repo's `.env` (the top folder, next to `pyproject.toml`). Variables already set in the shell win over the file. If the file isn't there, `lab-os serve` logs `no …/.env: no API keys` with the exact path it looked for. `new-place` never copies a `.env`, so keys never spread to a new place.
- **The lab's protected devices come along to every place:** anything `off_limits: true` in the repo's `config/devices.yaml` is refused at every place, and anything `borrowed: true` (the green arms and their cameras, since step 11) keeps its rules at every place (no motor setup or calibration, driven with a copy of the training calibration, which is only read), even if another folder's `devices.yaml` lists it differently. They're only drivable where a venue lists them in `active_devices`. Switching folders can never weaken them.
- **Two kinds of protection in `devices.yaml`:** `off_limits: true` = never opened (refused by name, port and USB serial; an entry without a serial blocks that whole USB model). `borrowed: true` = another project's device: lab-os may drive or use it, but `so101_setup` refuses it (also by board serial), it's never a command-line default, and `training_calibration: robots/so_follower/sheep.json` names its training calibration in LeRobot's cache (read only, the source of truth): lab-os drives with its copy in `calibration/<name>/` and refuses if the two differ.
- **One program per port, everywhere:** before an SO-101 port or a camera is opened, lab-os checks that no other program has it open (`/proc` on Linux, `lsof` elsewhere) and refuses with a sentence naming it.
- **An arm's table height:** `table_z_cm` (default 0) is where the table is in the arm's own heights, whose 0 is the bottom of its base: negative for an arm standing on a plate (`so101-white`: −1.6). The AI tools, `pick_at`, the floor and teleop then measure every height from the table (quick job 28).
- **Cameras by socket:** identical cameras share a serial, so a camera is `kind: camera` with `socket: usb-0:7` (the USB part of its `/dev/v4l/by-path/` name; `ls -l /dev/v4l/by-path/` lists them without opening anything). Never `/dev/videoN`.

## Your own arm
Add it to your `devices.yaml` (by `/dev/serial/by-id/…` path and USB serial, like the lab's), add its name to your venue's `active_devices`, then `lab-os serve --config ~/my-lab-os --arm <its name>`. `--arm` accepts `fake`, `fake-xarm1` or any SO-101 (`kind: so101`) or xArm (`kind: xarm1s`) in the place's device list. Calibration files go to the repo's `calibration/<arm name>/` (one folder per arm, so a home arm with its own name never touches the lab's).
