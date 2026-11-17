#!/usr/bin/env bash
# One-off (2026-11-17): make LeLab use a COPY of the green arms' training calibration.
# The training files (sheep.json = follower, shepherd.json = leader) are the source of truth:
# this script only reads them. Run it yourself (Claude's hook blocks this folder):
#     bash ~/lab-os/scripts/green-lelab-from-training.sh
# What it does, all inside ~/.cache/huggingface/lerobot (LeRobot's cache):
#   1. a backup of the whole calibration/ and robots/ folders in ~/green-calibration-backup/
#   2. LeLab's own copies: so_follower/lelab_green.json (= sheep), so_leader/lelab_green.json (= shepherd)
#   3. one LeLab entry, SO-101_Green, that uses those copies (no cameras: add them in LeLab if needed)
#   4. MOVES (not deletes) the two old entries, LeLab's two old calibration files and the stray
#      follower-folder shepherd.json into the backup's old-lelab/ folder
# Nothing is deleted; to undo, move the files back from the backup.
set -euo pipefail

C=~/.cache/huggingface/lerobot
CAL=$C/calibration
B=~/green-calibration-backup
F=$CAL/robots/so_follower
L=$CAL/teleoperators/so_leader

if pgrep -f "uv/tools/lelab" >/dev/null; then
  echo "LeLab is running: close it first (Ctrl+C in its terminal), then run this again."; exit 1
fi
for f in "$F/sheep.json" "$L/shepherd.json"; do
  [ -f "$f" ] || { echo "Missing $f: stopping, nothing changed."; exit 1; }
done

# 1. backup (never overwrites an earlier one)
if [ ! -d "$B/before-2026-11-17" ]; then
  mkdir -p "$B/before-2026-11-17"
  cp -rp "$CAL" "$C/robots" "$B/before-2026-11-17/"
fi
mkdir -p "$B/old-lelab"

# 2. LeLab's copies of the training files
cp -pn "$F/sheep.json" "$F/lelab_green.json"
cp -pn "$L/shepherd.json" "$L/lelab_green.json"
cmp -s "$F/sheep.json" "$F/lelab_green.json" && cmp -s "$L/shepherd.json" "$L/lelab_green.json" \
  || { echo "A lelab_green.json already existed and differs from the training file: check it."; exit 1; }

# 3. the one entry (ports as LeLab saved them before)
if [ ! -f "$C/robots/SO-101_Green.json" ]; then
  cat > "$C/robots/SO-101_Green.json" <<'EOF'
{
  "name": "SO-101_Green",
  "leader_port": "/dev/ttyACM0",
  "follower_port": "/dev/ttyACM1",
  "leader_config": "lelab_green.json",
  "follower_config": "lelab_green.json",
  "cameras": []
}
EOF
fi

# 4. move the old ones out of LeLab's sight
for f in "$C/robots/SO-101_Green_Follower.json" "$C/robots/SO-101_Green_Leader.json"; do
  [ -f "$f" ] && mv -n "$f" "$B/old-lelab/entry-$(basename "$f")"
done
[ -f "$F/SO-101_Green_Leader.json" ] && mv -n "$F/SO-101_Green_Leader.json" "$B/old-lelab/follower-SO-101_Green_Leader.json"
[ -f "$L/SO-101_Green_Follower.json" ] && mv -n "$L/SO-101_Green_Follower.json" "$B/old-lelab/leader-SO-101_Green_Follower.json"
[ -f "$F/shepherd.json" ] && mv -n "$F/shepherd.json" "$B/old-lelab/follower-folder-shepherd-mixup.json"

echo; echo "Done. LeLab now has one entry, SO-101_Green, using copies of the training calibration."
echo "Follower folder:"; ls -l "$F"; echo "Leader folder:"; ls -l "$L"; echo "LeLab entries:"; ls -l "$C/robots"
echo "Backup: $B"
