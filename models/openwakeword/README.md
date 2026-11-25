# openWakeWord models (the wake word, focus step 7)

From **openWakeWord** 0.6.0 (David Scripka, https://github.com/dscripka/openWakeWord), downloaded 2026-11-12 with its `download_models(["hey_jarvis"])`. lab-os runs them with `onnxruntime` itself (`src/lab_os/ai/wake.py`), without the `openwakeword` package (on Linux it needs `tflite-runtime`, which has no Python 3.12 build).

| File | What | sha256 |
|---|---|---|
| `melspectrogram.onnx` | audio (16 kHz) → mel spectrogram | `ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f` |
| `embedding_model.onnx` | mel frames → speech embeddings (Google's speech_embedding, re-implemented) | `70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f` |
| `hey_jarvis_v0.1.onnx` | 16 embeddings → "hey jarvis" score 0–1 | `94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb` |

**Licenses:** openWakeWord's code is Apache 2.0. Its **pre-trained models are CC BY-NC-SA 4.0** (attribution, **non-commercial**, share-alike): fine for the lab's non-commercial use; a commercial use would need other models (e.g. Porcupine, `docs/archive/guides-2026-11-25/voice.md`). The embedding model is based on Google's speech_embedding (Apache 2.0).

Another phrase = another model file here (openWakeWord ships "alexa", "hey mycroft", "hey rhasspy"; custom ones can be trained) and the persona's `wake_word:` naming it.

## More wake words (quick job 90, 2026-11-22)
From the community collection **fwartner/home-assistant-wakewords-collection** (https://github.com/fwartner/home-assistant-wakewords-collection, MIT license, 578 stars, branch `main`), downloaded 2026-11-22. They are openWakeWord models (16 embeddings × 96 in, one score out), trained by different people. Each is about 200 KB.

| File here | Source in the collection | Phrase | sha256 |
|---|---|---|---|
| `ok_computer.onnx` | `en/ok_computer/ok_computer.onnx` | "OK computer" | `720098d1c0d818e558a6782513965c6275f902f83e2c74d32417a4f15778afac` |
| `tars.onnx` | `en/TARS/TARS.onnx` | "TARS" | `f9e361f991ba6d898abd0f4dc025fbfc5779dcde9b950cb4bb3837d2313cdc62` |
| `hey_friday.onnx` | `en/hey_friday/hey_Friday!.onnx` | "hey Friday" | `a5a51b398426db79bd4a6d058b5928bb2c0cfe946db24a974845652f00dcae57` |

On macOS's `say` voice (2026-11-22), each scored on its own phrase only: OK computer 0.88, hey Friday 0.88, TARS 0.42 (under the default threshold of 0.5). No model was found for KAREN or EDITH. Plain "computer" was left out on purpose: people say it all day in a computer lab. **If one wakes badly in the lab, drop it** (its file here and its line in `PHRASES`, `src/lab_os/ai/wake.py`).
