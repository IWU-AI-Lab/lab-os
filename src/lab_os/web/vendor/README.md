# Vendored browser libraries

Saved in the repo (not loaded from a CDN) so the pages work offline, at demo venues and on the Quest over USB. Every page shares them (served at `/web/vendor/`). Pages map the bare `three` imports to these files with an import map (`src/lab_os/teleop/web/index.html`, `monitor.html`).

| Library | Version | License | Files kept |
|---|---|---|---|
| [three.js](https://threejs.org) (npm `three`) | 0.186.1 | MIT (`three/LICENSE`) | `build/three.module.js`, `build/three.core.js`; `examples/jsm/controls/OrbitControls.js`; `examples/jsm/loaders/{STLLoader,ColladaLoader,TGALoader}.js` + `loaders/collada/` (ColladaLoader is imported by urdf-loader) |
| [urdf-loader](https://github.com/gkjohnson/urdf-loaders) (npm `urdf-loader`) | 0.13.1 | Apache-2.0 (`urdf-loader/LICENSE`, from the GitHub tag `v0.13.1`) | `src/URDFLoader.js`, `src/URDFClasses.js` |
| Fonts (`fonts/`): Chakra Petch, Doto, Inter, JetBrains Mono, Orbitron, Oxanium, Rajdhani, Share Tech Mono (Google Fonts, downloaded 2026-11-10); DSEG7/DSEG14 Classic Bold (keshikan/DSEG, the subset the design concept embedded) | as served by Google Fonts on 2026-11-10 | SIL Open Font License 1.1 (`fonts/OFL.txt`, one notice per family) | the latin subset `.woff2` only; `fonts/fonts.css` declares them (the designed hub links it) |

Files are unmodified copies from the npm tarballs (`registry.npmjs.org/<name>/-/<name>-<version>.tgz`). No Node.js needed.

To update: download the new tarball, copy the same files over (keep the paths, the import map depends on them), update this table, and check the 3D view still loads (`uv run lab-os-teleop replay tests/fixtures/sample_clutch.jsonl --loop`, open `/monitor`).

Fonts: re-download from `fonts.googleapis.com/css2?family=…` with a current browser's user agent (it then answers with `.woff2`), keep the `/* latin */` blocks, and rewrite `fonts.css` (theme.yaml `font.bundled` lists the families).
