# Smart Turn (the end of a spoken question, quick job 110)

From **Pipecat's Smart Turn v3** (Daily, https://github.com/pipecat-ai/smart-turn, about 1,700 stars; the model at https://huggingface.co/pipecat-ai/smart-turn-v3), downloaded 2026-11-25. **License: BSD 2-clause** (code and model). lab-os runs it with `onnxruntime` itself (`src/lab_os/ai/turn.py`), without Pipecat or `transformers`: Whisper's log-mel features are made in numpy (tested against `transformers.WhisperFeatureExtractor`, `tests/test_turn.py`).

| File | What | sha256 |
|---|---|---|
| `smart-turn-v3.2-cpu.onnx` | the last 8 s of 16 kHz audio (as an 80 × 800 log-mel spectrogram) → "the turn is finished" 0–1 (int8, 8.7 MB; Whisper Tiny's encoder and a small classifier) | `2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f` |

On the Mac (M-series), one check takes about 37 ms (the first one, with the load, about 0.2 s). On macOS's `say` voice: "What time is it?" 0.97, "Calculate 37 times 48, and then" 0.01, "Tell me about the, um" 0.01.
