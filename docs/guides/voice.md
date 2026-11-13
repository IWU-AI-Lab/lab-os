# Voice: talk to the hub

The hub's assistant hears and answers aloud (focus step 7). **Typing never changes:** where voice can't work, there's simply no mic button.

## Try it (push-to-talk)
1. A key in `.env` in the repo's top folder: `GEMINI_API_KEY=…` is enough (the free key). Restart the brain after editing `.env`.
2. `uv run lab-os serve`, open **http://localhost:8080/** (or `/design`) **on the brain's own computer**, start the hub.
3. A **mic button** appears next to "Ask anything". **Hold it (or hold Space) and talk; let go.** Your words appear above the answer while you talk; the answer streams in under the core and is spoken. The core shows `listening` while you hold, then `thinking`, then `speaking`, moving with the real loudness of the voice.
4. Esc while it listens: nothing is asked. Esc (or holding the mic again) while it speaks: it stops talking.

The first press asks the browser for the microphone; allow it once. The microphone stays open for a minute after the last press (so the next question's first word isn't lost), then the browser's recording sign goes away.

**No mic button?** It shows only when all of these are true; hover the place where it would be, or see `voice` in `/api/status` for the brain's reason:
- the page is **secure**: `http://localhost` or `https://`. From another computer by the brain's IP address (`http://192.168…`), browsers refuse the microphone ("Secure pages" below for the ways around it);
- the browser lists a **microphone** (it reacts to plugging and unplugging);
- the brain has **voice**: the persona's `voice:` isn't `none`, a voice setup has its key, there's internet, and the chat isn't paused (no key, budget used up).

## Secure pages (the microphone on other screens)
Browsers give the microphone (and Wake Lock, app install, WebXR) only to `https://` or `http://localhost` pages. The lab's real address (`hub.indwesailab.com` with a Let's Encrypt certificate via Route 53) is **deferred** (decision 2026-11-10; the router side: `docs/guides/network-setup-checklist.md` → Step 7). Until then, easiest first:
- **The brain's own screen:** `http://localhost:8080` (a monitor or the Newline on the brain's HDMI counts).
- **Chrome's flag** on another screen: `chrome://flags` → "Insecure origins treated as secure" → `http://<brain's address>:8080`, then relaunch; on a kiosk, `--unsafely-treat-insecure-origin-as-secure=http://<brain's address>:8080`.
- **`adb reverse`** over USB (the Quest, an Android device): the page is `http://localhost:8080` there too.
- **Tailscale's certificate** (an idea: `docs/plan/ideas.md` → "Demo away from the lab").

No secure page or no microphone: no mic button; typing works.

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
- **The room microphone:** from across the room it needs a decent microphone (a conference speakerphone or a microphone array; weak USB dongles only hear you up close). At the lab (2026-11-13) the desktop's USB microphone heard it at the desk, sometimes only when spoken louder; on the Quest it usually fires and sometimes misses (`docs/dev/GOTCHAS.md`).

## In VR (`/xr`)
The hub in VR is a screen like the others, with the headset's own microphone and speakers:
- **Push-to-talk:** point at the ask line under the core and hold the trigger (or a pinch); let go when you're done. The answer types out under the core as it's spoken.
- **The wake word:** on whenever the brain offers it (no per-screen setting in VR: the headset is personal), while the hub is up with no page or module open; the dot in the strip says it's listening.
- **Another screen's turns:** a question heard by the desktop (its push-to-talk or its wake word) shows under the core in VR too, from the brain's conversation (`/api/chat`); the desktop speaks the answer, and the core follows the brain's state.
- **The microphone permission** is asked on the page before entering VR ("Allow the microphone"): a browser prompt inside VR is easy to miss. The Quest's browser reaches the brain as `http://localhost:8080` (adb reverse), a secure page, so the microphone is allowed.
- No voice (no key, no internet, paused): the ask line says why when held.

## The spoken greeting
After the start tap, the greeting ("Good morning." + one line of real news, `docs/dev/personas.md` → "The greeting") is also **spoken**, with a hint how to talk ("You can talk to me: hold the mic.", "tap the mic." with dictation, 'say hey Jarvis.' with the wake word). On the designed hub, the speech is asked for at the start tap and plays while the greeting is typed under the title after the jump, so there's no wait. The start tap is what lets the browser play it.
- Only where voice works at the brain (see "No mic button?" above, minus the microphone) and this screen's sound is on (⚙ → This screen, or `?sound=0`). No voice or no internet: silent, as before.
- A screen without a microphone (or not a secure page) hears the greeting without the hint.
- Holding the mic (or Space) during the greeting cuts it short.

## How it works
- **The page records and plays; the brain hears, thinks and speaks** (`/ws/voice`, `docs/dev/protocol.md` → "Voice"). API keys never leave the brain.
- The page sends the microphone as 16 kHz audio while the mic is held (with the browser's echo cancellation, so the speakers stay out of it). The brain passes it to the voice service, which **hears while you talk**: the words come back as they're recognized.
- On release, the words go into **the same conversation as typing**: the persona, the read tools, the history, the spend cap, the assistant's states. Spoken questions show up in History like typed ones.
- **The text appears as it's said:** a spoken answer's words show up under the core while that part is spoken, not when the AI writes them (the core stays `thinking` until the voice starts). If no voice comes (an error, the limit), the text shows anyway.
- The answer is spoken **sentence by sentence**: the first sentence as soon as it's written, the rest while that one plays. A drafted prompt ("Prompt: …") isn't read out ("The prompt is on the screen."), links neither; after about 900 characters it says "The rest is on the screen."
- If the voice service fails (e.g. the free key's limit), the answer stays on the screen and a short note says why.

## Voice setups (`config/models.yaml` → `voices:`)
Like the chat's setups: the persona picks one by name (`voice: main` in `config/personas/<id>.yaml`; `none` = no voice), `fallback` is used when a setup's key is missing, and switching is a config edit.
| Setup | Service | Hears | Speaks | Key |
|---|---|---|---|---|
| `main` | OpenAI | `gpt-4o-mini-transcribe` (after the release) | `gpt-4o-mini-tts`, voice `fable`, British and lively, speed 1.15 | `OPENAI_API_KEY` |
| `backup` | Gemini, free key | `gemini-3.5-transcribe-live` (while you talk) | `gemini-3.8-flash-lite-tts` (then 3 more), voice `Charon` | `GEMINI_API_KEY` |

- `main` falls back to `backup` while there's no OpenAI key, so today the free Gemini key does everything. When the professor's OpenAI key is in `.env`, `main` is used: no code change.
- `speak` can be a list: when a model is over its limit, the next one speaks. **Gemini's free key allows only 3 speech requests a minute per model**, and an answer uses 2 (the first sentence, then the rest), the greeting 1. With the four free TTS models listed, that's ~12 a minute, about 6 spoken answers. Past that, the answer stays on the screen with a note until a model is free again (the brain waits out each model's retry time, ~1 minute). **And only 10 a day per model** (checked 2026-11-12): ~40 spoken pieces a day, about 15–20 answers with the greeting. Testing uses them up too. A paid Gemini key or the OpenAI key (`main`) has no such limit. A model that's busy or stuck (no answer in 15 s) is skipped once.
- **How it sounds** (OpenAI): `style` is sent with every request as instructions (accent, mood, manner: the lab's is "a lively, warm British accent …"); `speed` sets the pace (1 = normal; the style alone doesn't change it). Gemini ignores both for now.
- `speaker` is the service's voice name. Gemini: `Charon`, `Kore`, `Puck`, `Fenrir`, `Aoede`, …; OpenAI: `onyx`, `alloy`, `nova`, ….
- `price_per_min` (`heard`, `spoken`) feeds the spend log: each voice turn adds lines with `kind: voice`, the seconds heard and spoken, and the cost. The free key costs $0, but Google may use the audio to improve its products, and it has limits per minute and per day.
- **Timing on the free key** (2026-11-12): the words are final ~0.4 s after you let go; the chat's answer takes 3–11 s (`gemini-3.5-flash-lite`, GOTCHAS); speaking a sentence ~2–3 s. The paid OpenAI chat is usually faster.

## Privacy
Voice goes to the voice service only while the mic is held, or after the wake word until the question ends. Listening for the wake word happens on the brain only. Questions asked by voice are kept like typed ones (`docs/dev/chat.md` → "Kept for a while"). On a public screen, anyone can hold the mic.
