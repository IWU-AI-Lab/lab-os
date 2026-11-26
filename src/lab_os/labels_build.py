"""Build the labels model from a list of words (`uv run lab-os labels build` runs this file).

It runs in a temporary environment with Ultralytics (`uv run --no-project --with ultralytics …`),
never in lab-os's own, so it imports nothing from lab-os. YOLOE-26m's weights and its text model
(MobileCLIP) are downloaded into the build folder (about 330 MB, not in git), the words become the
model's classes, and the model is exported to ONNX. After that, lab-os needs neither the internet
nor Ultralytics.

    python labels_build.py WORDS.json OUT.onnx BUILD_FOLDER
"""

import json
import os
import shutil
import sys
from pathlib import Path

WEIGHTS = "yoloe-26m-seg.pt"  # the segmentation weights; lab-os uses only the boxes


def main(words_json: str, out: str, build: str) -> int:
    from ultralytics import YOLOE

    words = json.loads(Path(words_json).read_text())
    target = Path(out).resolve()
    Path(build).mkdir(parents=True, exist_ok=True)
    os.chdir(build)  # Ultralytics downloads into the current folder
    model = YOLOE("yoloe-26m.yaml").load(WEIGHTS)  # boxes only: no mask head
    model.set_classes(words, model.get_text_pe(words))
    made = model.export(format="onnx", imgsz=640, simplify=True)
    shutil.move(made, target)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
