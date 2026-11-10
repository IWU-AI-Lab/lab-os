# The hub's chat (typed)

The assistant under the hub's circle answers typed questions (focus step 5). It **only reads and answers**: from the hub it can't change or move anything (focus rule 5).

## Try it
1. Put a key in `.env` (repo top folder; copy `.env.example` if there's none). The names, exactly:
   - `OPENAI_API_KEY=…`: the `main` setup (OpenAI).
   - `GEMINI_API_KEY=…`: the `backup` setup (Gemini). Used automatically when there's no OpenAI key.
2. `uv run lab-os serve`, open http://localhost:8080/, start the hub.
3. Type anywhere (it lands in "Ask anything"), press Enter. The answer streams in under the circle; **History** (or a tap on the answer) opens the whole conversation; Back or Esc closes it.

The status strip says which setup answers (`AI: main (OpenAI)`), or `AI not connected` / `AI: paused`. The brain checks the service every minute by listing its models (costs nothing). Without internet the assistant shows `offline`, and everything else keeps working.

## AI setups (`config/models.yaml`)
Every setup speaks the OpenAI-style chat interface (`POST …/chat/completions`), so they differ only by **address, model name and key name**:
| Setup | Where | Model | Key |
|---|---|---|---|
| `main` | OpenAI | `gpt-6-luna` ($0.10 / $0.50 per 1M tokens in / out) | `OPENAI_API_KEY` |
| `backup` | Gemini's OpenAI-compatible address | `gemini-3.5-flash-lite` (free key: $0) | `GEMINI_API_KEY` |
| `local` | Ollama on this computer, no internet | `qwen3:4b` | none |

- `fallback: backup` on `main`: no OpenAI key → the backup answers. Only a **missing key** switches; an error doesn't (it shows the error).
- **Switching:** the persona picks the setup (`model: main` in `config/personas/<id>.yaml`, `docs/personas.md`). Change it there, or edit the setups in `models.yaml`; the brain re-reads both before every answer (no restart).
- **Local:** `ollama serve`, `ollama pull qwen3:4b`, then point `main` at the `local` values (or give a home place its own `models.yaml`, `docs/places.md`). On the lab desktop, mind the GPU: it's shared with the training project. llama.cpp's server also works but defaults to port 8080, the hub's port: start it on another port.
- `options` are sent with every request as they are (e.g. `reasoning_effort: none`, `max_completion_tokens: 800` for OpenAI; Gemini wants `max_tokens`).
- Prices are in the file (checked 2026-11-09); they only feed the spend log, so keep them current.

## Spend and the budget
- Every answer is logged in `logs/ai-spend/<YYYY-MM>.jsonl`: time, setup, model, tokens in / cached / out, cost. If a service doesn't report tokens, it's estimated (~4 characters per token) and marked `estimated`.
- **Budget:** `ai_budget_usd_month` in `config/place.yaml` (the lab: $20). When this month's spend reaches it, the chat pauses with a full sentence ("This month's AI budget ($20.00) is used up, so the chat is paused until the 1st. Everything else on the hub still works."). It starts again on the 1st, or when you raise the number (no restart needed).
- The **AI Spend** panel shows the month's total against the budget. A venue with `public: true` hides it (a hallway screen).

## What it knows
The system prompt is the persona's personality text (`config/personas/<id>.md`, `docs/personas.md`) plus a few fixed rules: the place's name, the date and time, "you can't change or move anything", short plain-text answers. Up to the last 20 messages go along with each question. The conversation starts with the greeting (the start press).

**It looks things up (step 6):** the chat gets the brain's MCP **read tools**: the project's docs (`project_status`, `read_doc`, `search_docs`, …), git history and the device list, plus `arm_status`. It uses them for "what's next?" or "what's on hold?", and **drafts a prompt to paste into Claude Code or Codex** ("Prompt:" + the text; History has a **Copy** button that copies the part after "Prompt:"). At most 4 look-ups per question; the status word under the circle says what it's reading. **Read only:** it gets only tools annotated read-only, never a move tool or `stop`. `docs/design/` is never served (the reveal is a surprise).

## Privacy and the public screen
Anyone at the screen can type. The conversation clears when the hub goes back to the start screen (after ~3 minutes with nobody there). Questions go to the AI service of the setup in use; a free Gemini key lets Google use them to improve its products, so don't type anything private into the backup.

Endpoints and the streamed message format: `docs/protocol.md` → "Chat".
