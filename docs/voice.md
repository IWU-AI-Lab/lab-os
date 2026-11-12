# Voice: talk to the hub

The hub's assistant hears and answers aloud (focus step 7). **Typing never changes:** where voice can't work, there's simply no mic button.

## Try it (push-to-talk)
1. A key in `.env` in the repo's top folder: `GEMINI_API_KEY=…` is enough (the free key). Restart the brain after editing `.env`.
2. `uv run lab-os serve`, open **http://localhost:8080/** (or `/design`) **on the brain's own computer**, start the hub.
3. A **mic button** appears next to "Ask anything". **Hold it (or hold Space) and talk; let go.** Your words appear above the answer while you talk; the answer streams in under the core and is spoken. The core shows `listening` while you hold, then `thinking`, then `speaking`, moving with the real loudness of the voice.
4. Esc while it listens: nothing is asked. Esc (or holding the mic again) while it speaks: it stops talking.

The first press asks the browser for the microphone; allow it once. The microphone stays open for a minute after the last press (so the next question's first word isn't lost), then the browser's recording sign goes away.

**No mic button?** It shows only when all of these are true; hover the place where it would be, or see `voice` in `/api/status` for the brain's reason:
- the page is **secure**: `http://localhost` or `https://`. From another computer by the brain's IP address (`http://192.168…`), browsers refuse the microphone (`current-focus.md` → "Secure pages" for the ways around it);
- the browser lists a **microphone** (it reacts to plugging and unplugging);
- the brain has **voice**: the persona's `voice:` isn't `none`, a voice setup has its key, there's internet, and the chat isn't paused (no key, budget used up).

## The way in, per screen
⚙ → **This screen** → **Talking to it**: how this screen listens. Kept in this screen's browser, like its level of detail, so each screen has its own.
- **push-to-talk** (the default): hold the mic (or Space), talk, let go; it answers aloud.
- **wake word**: say **"hey Jarvis"** from anywhere in the room, then your question; it answers aloud. Push-to-talk still works. See "The wake word" below.
- **dictation**: tap the mic (or tap Space with the ask line empty). The words go **into the ask line** while you talk. It stops after a short silence (~1.6 s once you've said something; 8 s if you say nothing), a second tap, or Space. **Enter** stops and sends; **Esc** or any other key stops and keeps what's there. Then fix it and send it like typing. The answer comes as text, like a typed question.

The choice is greyed out, with the reason, where the screen can't listen at all (not a secure page, no microphone, the browser blocks the microphone). "wake word" is offered only where the brain can do it (the help text says why not). The mic button's tooltip says which way is on.

## The wake word
On a screen set to **wake word**, while the hub is up and awake (not on the start screen, not dimmed, no module open, the tab in front), the page streams its microphone to the brain. **The brain listens for the phrase itself**, with openWakeWord's models on its own CPU (~2 % of one core per screen): nothing goes to a voice service until the phrase is heard. A **small dot** in the status strip says it's listening for the phrase; it's separate from the core, whose `listening` starts only after the phrase (or a push-to-talk press).

After "hey Jarvis", the core listens like a push-to-talk press: say the question; it ends after ~1.5 s of quiet (nothing said in 6 s: it gives up), then it answers aloud. "Hey Jarvis, what's next?" in one breath works too (the phrase is taken off the question). Esc drops the question. It doesn't listen for the phrase while its own answer plays.
- **Where:** a secure page with a microphone the browser lets stay open (allowed once for the page). The browser shows its recording sign the whole time the dot is on.
- **Which phrase:** the persona's `wake_word:` (both personas: `hey_jarvis`; `none` = no wake word). openWakeWord ships "hey jarvis" (and "alexa", "hey mycroft", "hey rhasspy"); another phrase needs its model file in `models/openwakeword/` (custom ones can be trained; Porcupine is the paid alternative for custom words).
- **Venues:** `wake_word:` in the venue's file (⚙ → The assistant → Wake word in this venue): `on`, `off`, or `default` = **off on a `public: true` venue**, on otherwise. Restart the brain after changing it.
- **Several screens** hear it: the one that heard it best answers; the others ignore it.
- **The models** (`models/openwakeword/`, README there): openWakeWord's, run with `onnxruntime` directly (its own package doesn't install on Linux with Python 3.12). Non-commercial license (CC BY-NC-SA 4.0).
- **The room microphone:** from across the room it needs a decent microphone (a conference speakerphone or a microphone array; weak USB dongles only hear you up close). Not tried at the lab yet.

## The spoken greeting
After the start tap, the greeting ("Good morning." + one line of real news, `docs/personas.md` → "The greeting") is also **spoken**, with a hint how to talk ("You can talk to me: hold the mic.", "tap the mic." with dictation, 'say hey Jarvis.' with the wake word). On the designed hub, the speech is asked for at the start tap and plays while the greeting is typed under the title after the jump, so there's no wait. The start tap is what lets the browser play it.
- Only where voice works at the brain (see "No mic button?" above, minus the microphone) and this screen's sound is on (⚙ → This screen, or `?sound=0`). No voice or no internet: silent, as before.
- A screen without a microphone (or not a secure page) hears the greeting without the hint.
- Holding the mic (or Space) during the greeting cuts it short.

## How it works
- **The page records and plays; the brain hears, thinks and speaks** (`/ws/voice`, `docs/protocol.md` → "Voice"). API keys never leave the brain.
- The page sends the microphone as 16 kHz audio while the mic is held (with the browser's echo cancellation, so the speakers stay out of it). The brain passes it to the voice service, which **hears while you talk**: the words come back as they're recognized.
- On release, the words go into **the same conversation as typing**: the persona, the read tools, the history, the spend cap, the assistant's states. Spoken questions show up in History like typed ones.
- The answer is spoken **sentence by sentence**: the first sentence as soon as it's written, the rest while that one plays. A drafted prompt ("Prompt: …") isn't read out ("The prompt is on the screen."), links neither; after about 900 characters it says "The rest is on the screen."
- If the voice service fails (e.g. the free key's limit), the answer stays on the screen and a short note says why.

## Voice setups (`config/models.yaml` → `voices:`)
Like the chat's setups: the persona picks one by name (`voice: main` in `config/personas/<id>.yaml`; `none` = no voice), `fallback` is used when a setup's key is missing, and switching is a config edit.
| Setup | Service | Hears | Speaks | Key |
|---|---|---|---|---|
| `main` | OpenAI | `gpt-4o-mini-transcribe` (after the release) | `gpt-4o-mini-tts`, voice `onyx` | `OPENAI_API_KEY` |
| `backup` | Gemini, free key | `gemini-3.5-transcribe-live` (while you talk) | `gemini-3.8-flash-lite-tts` (then 3 more), voice `Charon` | `GEMINI_API_KEY` |

- `main` falls back to `backup` while there's no OpenAI key, so today the free Gemini key does everything. When the professor's OpenAI key is in `.env`, `main` is used: no code change.
- `speak` can be a list: when a model is over its limit, the next one speaks. **Gemini's free key allows only 3 speech requests a minute per model**, and an answer uses 2 (the first sentence, then the rest), the greeting 1. With the four free TTS models listed, that's ~12 a minute, about 6 spoken answers. Past that, the answer stays on the screen with a note until a model is free again (the brain waits out each model's retry time, ~1 minute). **And only 10 a day per model** (checked 2026-11-12): ~40 spoken pieces a day, about 15–20 answers with the greeting. Testing uses them up too. A paid Gemini key or the OpenAI key (`main`) has no such limit. A model that's busy or stuck (no answer in 15 s) is skipped once.
- `speaker` is the service's voice name. Gemini: `Charon`, `Kore`, `Puck`, `Fenrir`, `Aoede`, …; OpenAI: `onyx`, `alloy`, `nova`, ….
- `price_per_min` (`heard`, `spoken`) feeds the spend log: each voice turn adds lines with `kind: voice`, the seconds heard and spoken, and the cost. The free key costs $0, but Google may use the audio to improve its products, and it has limits per minute and per day.
- **Timing on the free key** (2026-11-12): the words are final ~0.4 s after you let go; the chat's answer takes 3–11 s (`gemini-3.5-flash-lite`, GOTCHAS); speaking a sentence ~2–3 s. The paid OpenAI chat is usually faster.

## Privacy
Voice goes to the voice service only while the mic is held, or after the wake word until the question ends. Listening for the wake word happens on the brain only. Questions asked by voice are kept like typed ones (`docs/chat.md` → "Kept for a while"). On a public screen, anyone can hold the mic.
