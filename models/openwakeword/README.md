# openWakeWord models (the wake word, focus step 7)

From **openWakeWord** 0.6.0 (David Scripka, https://github.com/dscripka/openWakeWord), downloaded 2026-11-12 with its `download_models(["hey_jarvis"])`. lab-os runs them with `onnxruntime` itself (`src/lab_os/ai/wake.py`), without the `openwakeword` package (on Linux it needs `tflite-runtime`, which has no Python 3.12 build).

| File | What | sha256 |
|---|---|---|
| `melspectrogram.onnx` | audio (16 kHz) → mel spectrogram | `ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f` |
| `embedding_model.onnx` | mel frames → speech embeddings (Google's speech_embedding, re-implemented) | `70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f` |
| `hey_jarvis_v0.1.onnx` | 16 embeddings → "hey jarvis" score 0–1 | `94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb` |

**Licenses:** openWakeWord's code is Apache 2.0. Its **pre-trained models are CC BY-NC-SA 4.0** (attribution, **non-commercial**, share-alike): fine for the lab's non-commercial use; a commercial use would need other models (e.g. Porcupine, `docs/guides/voice.md`). The embedding model is based on Google's speech_embedding (Apache 2.0).

Another phrase = another model file here (openWakeWord ships "alexa", "hey mycroft", "hey rhasspy"; custom ones can be trained) and the persona's `wake_word:` naming it.
