# Vendored browser libraries

Saved in the repo (not loaded from a CDN) so the pages work offline, at demo venues and on the Quest over USB. Every page shares them (served at `/web/vendor/`). Pages map the bare `three` imports to these files with an import map (`src/lab_os/teleop/web/index.html`, `monitor.html`).

| Library | Version | License | Files kept |
|---|---|---|---|
| [three.js](https://threejs.org) (npm `three`) | 0.186.1 | MIT (`three/LICENSE`) | `build/three.module.js`, `build/three.core.js`; `examples/jsm/controls/OrbitControls.js`; `examples/jsm/loaders/{STLLoader,ColladaLoader,TGALoader}.js` + `loaders/collada/` (ColladaLoader is imported by urdf-loader) |
| [urdf-loader](https://github.com/gkjohnson/urdf-loaders) (npm `urdf-loader`) | 0.13.1 | Apache-2.0 (`urdf-loader/LICENSE`, from the GitHub tag `v0.13.1`) | `src/URDFLoader.js`, `src/URDFClasses.js` |
| [MediaPipe Tasks Vision](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) (npm `@mediapipe/tasks-vision`), the hand landmarker model and the object detector model | 1.2.2; the models `hand_landmarker/float16/1` (downloaded 2026-11-19) and `efficientdet_lite0/float16/1` (downloaded 2026-11-26) | Apache-2.0 (`mediapipe/LICENSE`, from the GitHub repository `google-ai-edge/mediapipe`; the models are Google's, under the same license) | `vision_bundle.mjs`; `wasm/vision_wasm_internal.{js,wasm}` (the plain loader; the `_module_` copies aren't used); `hand_landmarker.task` from `storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/` (the webcam page, `/webcam`); `efficientdet_lite0.tflite` (7.3 MB, the 80 COCO kinds) from `storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/` (the Raspbot's labels in VR, quick job 128; the float16 model found the dogs in MediaPipe's test picture, the int8 one did not) |
| Fonts (`fonts/`): Chakra Petch, Doto, Inter, JetBrains Mono, Orbitron, Oxanium, Rajdhani, Share Tech Mono (Google Fonts, downloaded 2026-11-10); DSEG7/DSEG14 Classic Bold (keshikan/DSEG, the subset the design concept embedded) | as served by Google Fonts on 2026-11-10 | SIL Open Font License 1.1 (`fonts/OFL.txt`, one notice per family) | the latin subset `.woff2` only; `fonts/fonts.css` declares them (the designed hub links it) |

Files are unmodified copies from the npm tarballs (`registry.npmjs.org/<name>/-/<name>-<version>.tgz`). No Node.js needed.

MediaPipe: the wasm file is 14.6 MB, the hand model 7.8 MB and the object model 7.3 MB, the biggest files here; only the webcam page and the Raspbot's labels in VR (after LABELS is switched on) load them.

To update: download the new tarball, copy the same files over (keep the paths, the import map depends on them), update this table, and check the 3D view still loads (`uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop`, open `/monitor/so101`).

Fonts: re-download from `fonts.googleapis.com/css2?family=…` with a current browser's user agent (it then answers with `.woff2`), keep the `/* latin */` blocks, and rewrite `fonts.css` (theme.yaml `font.bundled` lists the families).
