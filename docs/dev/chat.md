# The hub's chat (typed)

The assistant under the hub's circle answers typed questions (focus step 5). It **reads, answers and opens pages** on the screen it's talking to (focus rule 5, decision 2026-11-14); it can't move the arms from the hub, except one fixed wave in visitor mode and, when Settings allows it, a named pose and the cube's hand-over (preview 4). With ⚙ → Assistant → Full Access on (quick job 80), it gets every tool of the brain (`docs/archive/guides-2026-11-25/hub.md` → "Full Access"; `src/lab_os/ai/tools.py`). On the brain's own computer it also has tools to start and exit visitor mode and (in visitor mode) to wave (quick job 35, `lab_os/hub/visitors.py`, `docs/archive/guides-2026-11-25/hub.md`), and, with ⚙ → Robots → The Assistant May Move the Arm, to move the arm to a pose, hand over the cube and let go (`lab_os/hub/arm_desk.py`, `docs/archive/guides-2026-11-25/hub.md` → "The assistant moves the arm"). What it can do is the tools it's given (the builder, 2026-11-14: no hard "never changes anything" rule, more abilities may come).

## Try it
1. Put a key in `.env` in the repo's **top folder**, next to `pyproject.toml` (copy `.env.example` there if there's none; not the one in `src/lab_os/place_template/`). Without it, the chat says which file it looked for. The names, exactly:
   - `OPENAI_API_KEY=…`: the `main` setup (OpenAI).
   - `GEMINI_API_KEY=…`: the `backup` setup (Gemini). Used automatically when there's no OpenAI key.
2. `uv run lab-os serve`, open http://localhost:8080/, start the hub.
3. Type anywhere (it lands in "Ask anything"), press Enter. Or hold the mic (or Space) and talk: `docs/archive/guides-2026-11-25/voice.md`. The answer streams in under the circle; **History** (or a tap on the answer) opens the whole conversation; Back or Esc closes it.

The status strip says which setup answers (`AI: main (OpenAI)`), or `AI not connected` / `AI: paused`. The brain checks the service every minute by listing its models (costs nothing). One failed check while connected is asked again twice, 3 s apart, before the hub says `AI not connected`, and every change is logged with its reason (`AI: main not reachable (HTTP 503)…`, `AI: main answers again`); the internet check likewise tries once more after a miss (since 2026-11-18, quick job 32: before, a single hiccup greyed the hub for 20 s while idle). Without internet the assistant shows `offline`, and everything else keeps working.

## AI setups (`config/models.yaml`)
Every setup speaks the OpenAI-style chat interface (`POST …/chat/completions`), so they differ only by **address, model name and key name**:
| Setup | Where | Model | Key |
|---|---|---|---|
| `main` | OpenAI | `gpt-6-luna` ($0.10 / $0.50 per 1M tokens in / out) | `OPENAI_API_KEY` |
| `strong` | OpenAI, thinking (quick job 69) | `gpt-6-luna` with `reasoning_effort: high` (same prices, more output tokens) | `OPENAI_API_KEY` |
| `backup` | Gemini's OpenAI-compatible address | `gemini-3.5-flash-lite` (free key: $0) | `GEMINI_API_KEY` |
| `local` | Ollama on this computer, no internet | `qwen3:4b` | none |

- **Real calculations** (quick job 86): the answering model always has a `calculate` tool. It writes a short Python program that sets `result` (`math`, `statistics`, plain builtins, loops; no imports), and the brain runs it in quick job 81's restricted runner (`lab_os.tools.program.calculate`, at most 5 s). The model then says the result with its steps, briefly. So a number is computed, not guessed: arithmetic, a flight's time, a reach, a unit change with several steps. No units library: `pint` brings three more packages, and the factors are plain math.
- **Harder questions go to `strong`** (quick job 69): the answering model gets a `think_hard` tool ("a plan with several steps, or a hard question not about the lab"; since quick job 86 not arithmetic, which goes to `calculate`). When it calls it, the hub says "Let me think about that." at once (spoken first), the brain asks `strong` (no tools, up to 120 s of quiet while it thinks), and the answering model says the result briefly. `strong`'s cost goes in the spend log under its own name. No tool when `strong` isn't usable or is the same as the answering setup (no OpenAI key: both fall back to `backup`).
- `fallback: backup` on `main`: no OpenAI key → the backup answers. Only a **missing key** switches; an error doesn't (it shows the error).
- **Switching:** the persona picks the setup (`model: main` in `config/personas/<id>.yaml`, `docs/dev/personas.md`). Change it there, or edit the setups in `models.yaml`; the brain re-reads both before every answer (no restart).
- **Local:** `ollama serve`, `ollama pull qwen3:4b`, then point `main` at the `local` values (or give a home place its own `models.yaml`, `docs/dev/places.md`). On the lab desktop, mind the GPU: it's shared with the training project. llama.cpp's server also works but defaults to port 8080, the hub's port: start it on another port.
- `options` are sent with every request as they are (e.g. `reasoning_effort: none`, `max_completion_tokens: 800` for OpenAI; Gemini wants `max_tokens`).
- Prices are in the file (checked 2026-11-09); they only feed the spend log, so keep them current.

## Spend and the budget
- Every answer is logged in `logs/ai-spend/<YYYY-MM>.jsonl`: time, setup, model, tokens in / cached / out, cost. If a service doesn't report tokens, it's estimated (~4 characters per token) and marked `estimated`. Voice lines are always marked `estimated` (since 2026-11-19).
- Every cost is lab-os's own estimate, and each brain counts only its own log (quick job 41): `docs/archive/guides-2026-11-25/hub.md` → "AI Spend". The real cost needs an OpenAI Admin key (not built; same section).
- **Budget:** `ai_budget_usd_month` in `config/place.yaml` (the lab: $20). When this month's spend reaches it, the chat pauses with a full sentence ("This month's AI budget ($20.00) is used up, so the chat is paused until the 1st. Everything else on the hub still works."). It starts again on the 1st, or when you raise the number: on the hub's **Settings → The assistant → Monthly AI budget**, or in `place.yaml` (no restart needed: the brain re-reads the number every time it checks, since 2026-11-14; a half-edited file keeps the last good number). The designed hub shows the sentence once, at the top; a question asked anyway nudges it instead of repeating it on the core (since 2026-11-18, quick job 31; before, a second copy appeared on the core and the core turned red).
- The **AI Spend** panel shows the month's total against the budget. A venue with `public: true` hides it (a hallway screen).

## What it knows
The system prompt is the persona's personality text (`config/personas/<id>.md`, `docs/dev/personas.md`) plus a few fixed rules: the place's name, the date and time, "your tools are what you can do now: you can't move the robot arms from here except with a tool made for it", short plain-text answers. Up to the last 20 messages go along with each question. The conversation starts with the greeting (the start press).

**It looks things up (step 6):** the chat gets the brain's MCP **read tools**: the project's docs (`project_status`, `read_doc`, `search_docs`, …), git history and the device list, plus `arm_status`. It uses them for "what's next?" or "what's on hold?", and **drafts a prompt to paste into Claude Code or Codex** ("Prompt:" + the text; History has a **Copy** button that copies the part after "Prompt:"). At most 4 look-ups per question; the status word under the circle says what it's reading. **Read only:** it gets only tools annotated read-only, never a move tool or `stop`. `docs/design/` is included since 2026-11-12 (the design isn't a surprise any more).

**A status report in one look-up (2026-11-16, quick job 16):** `lab_status` returns the arm (who drives it, held still, the warmest servo), the devices with the hub open, voice and the AI (connected, paused), internet, this month's spend and budget (never on a public venue; marked estimated and this brain only, so the model says "estimated", since 2026-11-19), the focus's next step, and warnings (limits switched off, warm servos, the chat paused). "How's the lab?" / "give me a status report" is one call; the tool tells the model to answer in a few sentences, warnings first. Only facts the brain has: what isn't known (whether a device is switched on) isn't in it.

**It opens pages (2026-11-14):** "pull up the Arm Control page", "show me the AI spend", "open the settings", "go back to the hub", typed or spoken, on the screen that asked. Each question carries what that screen can show (`pages`: the hub's module buttons, Settings, the callouts' pages, the conversation, `hub`); the model gets an `open_page` tool for exactly those, and the turn's `open` event makes the page show it, like a tap would (the other screens don't change). When a round only opens a page, the brain answers at once ("Here's Arm Control.", "Back to the hub.") instead of asking the model again, so it's spoken quickly. A page this screen doesn't have is refused to the model, which then says so. On the plain hub the callouts are on the hub itself: "show me the AI spend" goes back to the hub and highlights that panel. In VR: the module buttons and the callouts.

## Kept for a while
An accidental reset, a closed page or the brain restarting (even a power cut) doesn't lose the conversation:
- The brain saves it after every answer (`logs/chat/current.json`) and reads it back when it starts.
- The reset, or the start press, puts a conversation with a question in it aside (`logs/chat/previous.json`). Under the ask line, **Bring back the last conversation (2 questions, 3:41 PM)** swaps it back in. Press it again to swap back.
- Both files are deleted once they're older than `chat_keep_minutes` in `place.yaml` (30 by default). `0` keeps nothing and deletes what's there when the brain starts.
- After a restart: press start, then **Bring back**.
- Only one conversation is kept aside (the latest one). A list of past conversations is an idea for later (`docs/plan/ideas.md`).

## Privacy and the public screen
Anyone at the screen can type. The conversation clears from the screen when the hub goes back to the start screen (after 30 minutes with nobody there, `hub.reset_after_s`), but **Bring back** can show it again for `chat_keep_minutes`. On a hallway screen with visitors, consider a short time (e.g. `chat_keep_minutes: 5`). Questions go to the AI service of the setup in use; a free Gemini key lets Google use them to improve its products, so don't type anything private into the backup.

Endpoints and the streamed message format: `docs/dev/protocol.md` → "Chat".
