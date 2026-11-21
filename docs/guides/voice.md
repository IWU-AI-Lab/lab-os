# Voice: talk to the hub

The hub's assistant hears you and answers aloud (focus step 7). **Typing always works.** If voice cannot work on a screen, that screen has no mic button.

## Try it (push-to-talk)
1. Put a key in `.env` in the repository's top folder. The lab uses `OPENAI_API_KEY` (the professor's key). `GEMINI_API_KEY` (the free key) is enough to try. After you change `.env`, restart the brain.
2. Run `uv run lab-os serve`. Open **http://localhost:8080/** (or `/design`) **on the brain's own computer**, and start the hub.
3. A **mic button** shows next to "Ask anything". **Hold it (or hold Space) and talk. Then release it.** The answer shows under the core and is spoken. The core shows `listening` while you hold, then `thinking`, then `speaking`, and it moves with the real loudness of the voice. Only the screen that has the conversation shows these three. The other screens stay idle (since 2026-11-20, quick job 58).
4. Press Esc while it listens: nothing is asked. Press Esc (or hold the mic again) while it speaks: it stops.

The first press asks the browser for the microphone. Allow it once. The microphone stays open for one minute after the last press, so that the next question's first word is not lost. Then the browser's recording sign goes away.

**No mic button?** It shows only when all of these are true. Hover over its place, or look at `voice` in `/api/status`, for the brain's reason:
- The page is **secure**: `http://localhost` or `https://`. From another computer at the brain's IP address (`http://192.168…`), browsers refuse the microphone ("Secure pages" below).
- The browser has a **microphone** (it notices when you plug one in or remove it).
- The brain has **voice:** the persona's `voice:` is not `none`, a voice setup has its key, the internet works, and the chat is not paused (no key, budget used up).

## Secure pages (the microphone on other screens)
Browsers give the microphone (and Wake Lock, app install, WebXR) only to `https://` or `http://localhost` pages. The lab's own address (`hub.indwesailab.com`, with a Let's Encrypt certificate through Route 53) is **for later** (decision 2026-11-10; the router side: `docs/guides/network-setup-checklist.md` → Step 7). Until then, use one of these (the easiest first):
- **The brain's own screen:** `http://localhost:8080`. A monitor or the Newline on the brain's HDMI is also the brain's screen.
- **Chrome's flag** on another screen: open `chrome://flags`, find "Insecure origins treated as secure", add `http://<brain's address>:8080`, and relaunch. On a kiosk, start Chrome with `--unsafely-treat-insecure-origin-as-secure=http://<brain's address>:8080`.
- **`adb reverse`** over USB (the Quest, or an Android device): there the page is also `http://localhost:8080`.
- **Tailscale's certificate** (an idea: `docs/plan/ideas.md` → "Demo away from the lab").

## The way in, for each device
⚙ → **This Device** → **Talking to It** sets how this device listens. The brain keeps the setting under the device's name (`?device=` in the hub's address, `docs/guides/hub.md` → "Devices"), so each device has its own. A page with no name keeps it in its browser.
- **Push-to-Talk** (the default): hold the mic (or Space), talk, release. It answers aloud.
- **Wake Word:** say **"hey Jarvis"** from anywhere in the room, then your question. It answers aloud. Push-to-Talk still works. See "The wake word" below.
- **Dictation:** tap the mic (or tap Space when the ask line is empty). The words go **into the ask line** while you talk. It stops after a short silence (about 1.6 s after you start talking; 8 s if you say nothing), after a second tap, or when you press Space. **Enter** stops and sends. **Esc** or any other key stops and keeps the words. Then correct them and send, as for typing. The answer comes as text, as for a typed question.

If the screen cannot listen at all (not a secure page, no microphone, the browser blocks the microphone), the choice is gray and says why. "Wake Word" shows only where the brain can do it; the help line says why not. The mic button's tooltip says which way is on.

## The wake word
On a screen set to **Wake Word**, the page sends its microphone to the brain while the hub is open and awake: not on the start screen, not dimmed, and the tab in front. It also listens while a module or a page is open, so "hey Jarvis, go back to the hub" works.

**The brain listens for the phrase itself,** with openWakeWord's models on its own CPU (about 2 % of one core for each screen). Nothing goes to a voice service until the brain hears the phrase. A **small dot** in the status strip shows that it listens for the phrase. The dot is separate from the core: the core's `listening` starts only after the phrase (or a push-to-talk press).

After "hey Jarvis", a short, quiet two-note sound says that it heard you (only where the device's sound is on). Then the core listens, as for a push-to-talk press. Say the question. The question ends when the voice service hears the pause after it (about 0.4 s), or after about 1 s of quiet on the page. If you say nothing for 6 s, it stops. Then it answers aloud. You can also say "Hey Jarvis, what's next?" in one breath (the brain removes the phrase from the question). Esc cancels the question.
- **Where:** a secure page with a microphone that the browser lets stay open (allow it once for the page). The browser shows its recording sign while the dot is on.
- **Which phrase:** the persona's `wake_word:` (both personas: `hey_jarvis`; `none` = no wake word). openWakeWord includes "hey jarvis" (and "alexa", "hey mycroft", "hey rhasspy"). Another phrase needs its model file in `models/openwakeword/`. You can train your own; Porcupine is the paid alternative for your own words.
- **Venues:** `wake_word:` in the venue's file (⚙ → Assistant → Wake Word in This Venue): `on`, `off`, or `default`. Default is **off on a `public: true` venue** and on in all other venues. After you change it, restart the brain.
- **More than one screen** hears it: the nearest one answers (quick job 70). The brain waits 0.3 s after the first screen for the others (before, 0.15 s). It picks the highest wake word score. Clear speech scores near 1.0 everywhere, so scores within 0.05 of the best count as a tie. Then the screen whose microphone heard the phrase loudest above its own room noise answers. The other screens show nothing. With one screen listening, it answers immediately. The brain's terminal logs each pick: `voice: newline (0.99, 21 dB), desk (0.98, 9 dB) heard the wake word: newline answers`.
- **"Hey Jarvis" stops a spoken answer** (since 2026-11-20, quick job 57). While the assistant thinks or speaks an answer to a spoken question, on any screen, say "hey Jarvis" or press the mic. The answer stops at once on every screen, and it listens to the new question. The text that came so far stays on the screen. The brain's terminal says `voice: desk's answer stopped: the wake word`. Before, the phrase was ignored until the answer had played.
- **No screen wakes while someone asks:** while a screen hears a question, and while the assistant answers a typed question (typed answers are not spoken, so they are not stopped). The brain's terminal says when it ignored the phrase, and why ("voice: desk heard the wake word, ignored: newline is hearing a question").
- **The answer says the phrase itself** (the greeting: "say hey Jarvis"): the microphones hear it from the speaker. The phrase is then ignored until that part has played, plus 1.5 s.
- **Sensitivity, for each device:** ⚙ → This Device → **Wake Word Sensitivity**, a slider from 1 (fewest false wakes) to 9 (hears the most). It shows when the wake word is available. 5 is openWakeWord's own default (a score of 0.5). Make it higher for a noisy room or a weak microphone. Make it lower if it wakes by itself. The brain keeps it under the device's name, and it applies immediately. What each level does: below.
- **Assistant language, for each device** (since 2026-11-18, quick job 33): ⚙ → This Device → **Assistant Language**, Expects and Answers, each Any (the default) or English. (Expects was called Listens until 2026-11-20, quick job 46.)
  - **Answers: English** makes it answer in English, typed or spoken, in any language that it was asked in. The rule goes with each question too, because the start instructions alone let a Spanish question get a Spanish answer (lab check 9.13).
  - **Answers: Any** (the default) answers in English, and in another language only when the whole question is clearly in that language (since 2026-11-20, quick job 55). Before, the plain persona answered short or misheard spoken questions in German, Turkish or Portuguese: its prompt names no language, and speech-to-text sometimes guesses words in another language. JARVIS's prompt sounds English, so it stayed in English. The rule is now the same for every persona.
  - **A typed question gets a written answer only.** This is by design: the hub speaks only answers to spoken questions (and the visitors' welcome).
  - **Expects: English** is a hint to speech-to-text: it expects English, but it still hears other languages. OpenAI's transcription (`main`, the lab's voice) gets the language code and a short English prompt. Gemini's live transcriber (the `backup` free key) has no such setting, and an instruction to it made no difference in a test (2026-11-18). So with the free key, Expects does nothing.
  - **The log:** the brain's terminal shows the settings and the transcriber with each question, not the words: `voice: question on desk: expects English, answers any language, heard by OpenAI (gpt-4o-transcribe)`. When the words have letters of another script, the line ends with, for example, `letters not in English: Cyrillic`. A typed question logs its Answers setting.
  - It applies from the next question.
- **The Quest** (GOTCHAS 2026-11-13, 2026-11-14): when the page's sound or microphone stops (the headset slept, or the browser lost audio focus), the page notices within one second and starts it again. While it cannot, the dot in the strip turns orange on the hub pages ("Not hearing the microphone: press the mic once"; in VR, only the log shows it). The brain's terminal also shows it ("voice: quest sent no audio for the wake word for 12.3 s").

### Sensitivity: what the levels do
The slider sets openWakeWord's two settings (`src/lab_os/ai/wake.py` → `SENSITIVITY`): the **threshold** (the score that counts) and the **patience** (how many 80 ms steps in a row must be at or above it).
| Level | 1 | 2 | 3 | 4 | **5** | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| Threshold | 0.8 | 0.7 | 0.6 | 0.55 | **0.5** | 0.45 | 0.4 | 0.33 | 0.25 |
| Patience | 1 | 1 | 1 | 1 | **1** | 1 | 1 | 2 | 2 |

Measured on recordings (`tests/test_wake.py`, with added white noise, harder than a real room):
- **A quiet voice alone is not the problem.** The recording at 1 % of its loudness still scores 0.999.
- **Noise is the problem.** "Hey Jarvis" at 10 % loudness under loud noise scored about 0.40: missed at 5, heard at 8.
- Other speech under noise never scored above about 0.26, and noise alone up to about 0.2. So 8 and 9 also need two steps in a row.

The brain's terminal shows near misses: `voice: desk heard something like "hey Jarvis" (0.38; it takes 0.50 at sensitivity 5)`. If you see these while you say the phrase, make the slider higher.

**openWakeWord's other options, tried and not used (2026-11-14):**
- Its **Silero voice-activity filter** (`vad_threshold`) is to stop false wakes from noise that is not speech. But on the recordings it removed a real "hey Jarvis" in loud noise (0.98 → 0.00). A noisy room needs the opposite.
- Its **Speex noise suppression** needs the `speexdsp_ns` C package (Linux only). The browser already removes noise and echo and controls the gain before the audio gets to the brain.

### How fast (2026-11-14)
The brain times each step from the end of "hey Jarvis" to the first spoken word, and writes one line for each turn:
```
voice timing (desk, wake word, warm, ended by the pause): heard the phrase · this screen picked +1 ms · listening +2 ms · voice service ready +0 ms · question over +2.31 s · words final +0.40 s · first text +3.10 s · first audio sent +2.20 s · first word playing +60 ms · waited 5.76 s after the question
```
The last voice turns are also at **http://localhost:8080/api/voice/timings** (milliseconds from the detection, for each step). What makes it fast:
- **Detection:** openWakeWord's score passes 0.5 about 0.1 s *before* the phrase's last sound (on the recordings). There is nothing more to gain there.
- **Selecting the screen:** with one screen listening, it answers immediately. With more screens, it waits 0.15 s.
- **Connecting to the voice service:** with the Gemini voice, while a screen listens for the phrase, the brain keeps one Gemini Live hearing connected in advance (new every 4 minutes, one for the brain; while idle, it sends nothing and costs nothing). OpenAI's hearing has nothing to connect: it hears the recording after the question.
- **The first words:** the audio from 0.3 s before the detection also goes to the hearing, so "hey Jarvis what's next" in one breath keeps "what's". A leftover "…vis" at the start is removed.
- **The end of the question:** the voice service's own pause detection ends it (about 0.4 s after the words). If not, the page's 1 s of silence ends it. The page also learns the room's noise while it listens for the phrase, so a noisy room does not keep it "listening" for 20 s.
- **The answer:** the chat's connection opens while you still talk, and the voice's connection when the question ends. The brain keeps connections for one minute. The rest is the AI's thinking time and the speech service.
- **The models** (`models/openwakeword/`, with a README): openWakeWord's models, run with `onnxruntime` directly (its own package does not install on Linux with Python 3.12). License: non-commercial (CC BY-NC-SA 4.0).
- **The room microphone:** from across the room, it needs a good microphone (a conference speakerphone or a microphone array; small USB microphones hear you only when you are near). In the lab (2026-11-13), the desktop's USB microphone heard it at the desk, sometimes only when spoken louder. On the Quest it usually hears it and sometimes misses (`docs/dev/GOTCHAS.md`).

## Conversation mode (quick job 68)
The assistant keeps listening and answering, with no wake word, like the live voice modes of ChatGPT and Gemini.
- **Start it:** press the conversation button (two speech boxes) next to the mic, or say "Hey Jarvis, start a conversation".
- **While it is on:** a sign above the core says "In a conversation · say "that's all" to end", and the button is lit. Ask a question, as after the wake word. After the answer has played, it listens again by itself. While nobody talks, it keeps listening and says nothing.
- **End it:** say "that's all" (or "goodbye", "end the conversation"), press the button again, or press Esc. It also ends when lab-os stops, or when the voice service does not answer (the hub says why).
- **How it works:** the brain starts each next question as after the wake word. It does not use OpenAI Realtime or Gemini Live: those are full live audio modes, but they need a second audio pipeline and cost more. It listens only after the answer has played, so it does not hear itself.
- **In a noisy room:** it takes any speech as a question, also other people's talk. The question ends after a short quiet, so a steady fan does not keep it open. But two people talking near the microphone get an answer to what they said. Use it near the microphone, and end it when you are done. The VR hub has no button for it; the phrase works there.

## In VR (`/xr`)
The hub in VR is a screen like the others, with the headset's own microphone and speakers:
- **Push-to-talk:** point at the ask line under the core and hold the trigger (or a pinch). Release it when you are done. The answer shows under the core while it is spoken.
- **The wake word:** on when the brain offers it (VR has no setting for each screen: the headset is personal), while the hub is open with no page or module open. The dot in the strip shows that it listens.
- **Another screen's turns:** a question that the desktop heard also shows under the core in VR (from the brain's conversation, `/api/chat`). The desktop speaks the answer, and the core follows the brain's state.
- **The microphone permission:** press "Allow the microphone" on the page before you enter VR. A browser question inside VR is easy to miss. The Quest's browser uses `http://localhost:8080` (adb reverse), a secure page, so the microphone is allowed.
- **No voice** (no key, no internet, paused): the ask line says why when you hold it.

## The spoken greeting
After the start tap, the greeting is also **spoken**: the time of day and a hint about how to talk ("Good morning. You can talk to me: hold the mic.", "tap the mic." with dictation, 'say hey Jarvis.' with the wake word). The news line (`docs/dev/personas.md` → "The greeting") shows on the screen and is not spoken.

**From a recording** (decision 2026-11-13): each voice says each greeting once (morning, afternoon or evening × each hint). The brain keeps the WAV file in the place's `recordings/greetings/` (`~/lab-os/recordings/greetings/` in the lab; not in git). At each later start, it plays the file with **no voice request**, so the free key's daily requests stay for answers. A new voice (another setup, model, speaker, style or speed in `models.yaml`) or a changed line gets a new file name, so it is spoken one more time. A saved greeting also plays with no internet or with the budget used up. To make one again, delete its file. On the designed hub, the speech is asked for at the start tap and plays while the greeting shows under the title after the jump (about 6.5 s after the tap), so there is no wait. After **Back to the start screen** (⏻, or nobody there), the next start speaks it at once, because the startup was already seen (quick job 42). The start tap is what lets the browser play it.
- It plays only where the screen's sound is on (⚙ → This Device → Sound, or `?sound=0` to switch it off) and the persona has a voice. If it was never recorded and there is no voice now (no internet, no key, the budget): no sound.
- A screen without a microphone (or not a secure page) hears the greeting without the hint.
- Hold the mic (or Space) during the greeting to stop it.

## How it works
- **The page records and plays. The brain hears, thinks and speaks** (`/ws/voice`, `docs/dev/protocol.md` → "Voice"). API keys never leave the brain.
- The page sends the microphone as 16 kHz audio while you hold the mic (with the browser's echo cancellation, so that the speakers are not heard). The brain gives it to the voice service.
- When you release, the words go into **the same conversation as typing:** the persona, the read tools, the history, the spend limit, the assistant's states. Spoken questions show in History like typed questions.
- **The text shows as it is spoken:** a spoken answer's words show under the core while that part is spoken, not when the AI writes them. The core stays `thinking` until the voice starts. If no voice comes (an error, the limit), the text shows anyway.
- It speaks the answer **sentence by sentence:** the first sentence as soon as it is written, the rest while that one plays. It does not read a prompt that it wrote ("Prompt: …"; it says "The prompt is on the screen.") or links. After about 900 characters, it says "The rest is on the screen."
- If the voice service fails (for example, the free key's limit), the answer stays on the screen with a short note that says why.

## Voice setups (`config/models.yaml` → `voices:`)
They work like the chat's setups. The persona selects one by name (`voice: main` in `config/personas/<id>.yaml`; `none` = no voice). `fallback` is used when a setup's key is missing. To change, edit the config.
| Setup | Service | Hears | Speaks | Key |
|---|---|---|---|---|
| `main` | OpenAI | `gpt-4o-mini-transcribe` (after you release) | `gpt-4o-mini-tts`, voice `fable`, British and lively, speed 1.15 | `OPENAI_API_KEY` |
| `backup` | Gemini, free key | `gemini-3.5-transcribe-live` (while you talk) | `gemini-3.8-flash-lite-tts` (then 3 more), voice `Charon` | `GEMINI_API_KEY` |

- `main` uses `backup` when `.env` has no `OPENAI_API_KEY`. The professor's OpenAI key is in `.env` on the builder's laptop and the lab desktop (since 2026-11-18), so `main` hears, answers and speaks there. The free Gemini key is only the fallback. **What is different with OpenAI:** it hears the recording after you release, so the words show at the end, not while you talk. A question after the wake word ends on the page's 1 s of quiet. There is no daily limit on spoken answers.
- **One voice for each persona** (quick job 47): the persona's `voice:` names one voice setup (both personas: `main`, OpenAI's `fable`). The brain's terminal names the voice of each answer and of the greeting, for example `voice: answer on desk spoken by main (OpenAI, gpt-4o-mini-tts, voice fable)`. When it says "two models", the answer may have sounded like two people. Greeting recordings from before 2026-11-20 are made again once.
- **The free Gemini key's limits:** 3 speech requests a minute for each model, and 10 a day for each model (checked 2026-11-12). An answer uses 2 requests (the first sentence, then the rest), the greeting 1. `speak` can be a list: when a model is over its limit, the next model speaks. Another model can sound like another person with the same voice name (quick job 47). So an answer keeps the model that spoke its first part when it can, and a greeting that another model spoke is not kept as the recording. With the four free models, that is about 6 spoken answers a minute and about 15 to 20 answers a day. Tests also use them. After the limit, the answer stays on the screen with a note until a model is free again (the brain waits for each model's retry time, about 1 minute). A model that is busy or does not answer in 15 s is skipped once. A paid Gemini key or the OpenAI key has no such limit.
- **The sound (OpenAI):** `style` goes with every request as instructions (accent, mood, manner; the lab's is "a lively, warm British accent …"). `speed` sets the pace (1 = normal; the style alone does not change it). Gemini ignores both for now.
- `speaker` is the service's voice name. Gemini: `Charon`, `Kore`, `Puck`, `Fenrir`, `Aoede`, and others. OpenAI: `onyx`, `alloy`, `nova`, and others.
- `price_per_min` (`heard`, `spoken`) goes into the spend log: each voice turn adds lines with `kind: voice`, the seconds heard and spoken, the cost, and `estimated: true` (lab-os measured the seconds; the service did not report them). The free key costs $0, but Google can use the audio to improve its products.
- **Timing on the free key** (2026-11-12): the words are final about 0.4 s after you release. The chat's answer takes 3 to 11 s (`gemini-3.5-flash-lite`). Speaking a sentence takes about 2 to 3 s. The paid OpenAI chat is usually faster.

## Privacy
Voice goes to the voice service only while you hold the mic, or after the wake word until the question ends. Listening for the wake word happens on the brain only. The brain keeps questions asked by voice like typed questions (`docs/dev/chat.md` → "Kept for a while"). On a public screen, anyone can hold the mic.
