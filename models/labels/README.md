# The Raspbot's labels model (quick job 128)

**YOLOE-26m** from Ultralytics (https://github.com/ultralytics/ultralytics, tens of thousands of stars; YOLOE: "Real-Time Seeing Anything", THU-MIG). **License: AGPL-3.0** (code and weights). It is an open-vocabulary detector: the words in `config/labels.yaml` become its classes, also words outside the usual 80 COCO kinds.

The model file is not in git (82 MB). Make it on the brain's computer:

```bash
uv run lab-os labels build
```

The build runs Ultralytics 8.4.219 in a temporary environment (`src/lab_os/labels_build.py`), never in lab-os's own. It downloads `yoloe-26m-seg.pt` and the text model `mobileclip2_b.ts` into `build/` here (about 330 MB, not in git), and PyTorch into uv's cache the first time. It writes `yoloe-26m.onnx` (boxes only, 640 × 640 input, the words in its metadata `names`). lab-os runs it with onnxruntime on the processor (`src/lab_os/object_labels.py`); it needs neither the internet nor Ultralytics after the build.

| File | What |
|---|---|
| `yoloe-26m.onnx` | a 640 × 640 picture → for each of 8400 places a box and a score for each word (no NMS) |

On the lab desktop (2026-11-26), one 640 × 480 picture takes about 100 ms with 6 threads (76 ms with 8, 137 ms with 4). Ultralytics' test pictures gave the same objects and scores as Ultralytics' own predict.
