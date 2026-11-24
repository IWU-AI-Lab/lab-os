# Personas: who the assistant is

A persona is a config file, `config/personas/<id>.yaml`, plus a short text file for how it talks. It changes the name on screen, the personality, which AI setup answers, the voice, and later the picture and sounds. **The theme (colors, fonts) is the same for every persona.**

There are two:
| id | Name on screen | What it's for |
|---|---|---|
| `lab-assistant` | Lab Assistant | the default: plain name, simple circle, no character |
| `jarvis` | J.A.R.V.I.S. | the show persona: calm, precise, dry wit |

## Switching
The place has a default persona, and each venue can have its own (decisions 2026-11-10). The first of these that says one wins:
1. `--persona jarvis` on `lab-os serve` (just this run);
2. `LAB_OS_PERSONA=jarvis` in the shell or the place's `.env`;
3. `persona: jarvis` in the venue's file (`config/venues/<venue>.yaml`). Every venue starts with `persona: default`, which means "the place's", until someone changes it;
4. `persona: jarvis` in the place's `place.yaml` (the lab: `config/place.yaml`, `lab-assistant`);
5. otherwise the plain `lab-assistant`.

For example, to make visit days J.A.R.V.I.S.: `persona: jarvis` in `config/venues/visit-day.yaml`.

**Switching is a config edit + reload:** change `persona:` in the venue's file or `place.yaml` (or edit a persona file), then reload the hub page. No restart: the brain re-reads the files on every request. The status strip shows `Assistant: <name>`. An unknown or broken persona in the files falls back to `lab-assistant` with a warning in the brain's output, so the hub keeps working; a mistyped `--persona` stops the brain at start with the list of personas.

To try J.A.R.V.I.S. without editing anything: `uv run lab-os serve --persona jarvis`.

## The file
```yaml
version: 1                    # file format version
id: jarvis                    # plain name: the same as the file name
display_name: "J.A.R.V.I.S."  # show name (on screen)
personality: jarvis.md        # how it talks: a short text file next to this one
model: main                   # which AI setup (config/models.yaml; main falls back to backup)
voice: main                   # voice setup (models.yaml → voices; docs/guides/voice.md); none = no voice
speakers: { openai: fable, gemini: Charon }  # its own speaker for each voice service (else the setup's)
wake_word: hey_jarvis         # the wake word (docs/guides/voice.md); none = no wake word;
                              # ⚙ → Assistant → Wake Word wins (place.yaml → wake_words)
picture: { type: orb, style: calm-ring, color: primary }   # read by the designed hub (step 10)
lines:
  greeting: "All local systems are up."   # the greeting when there's no news
sounds: default               # sound pack
```
**Extensible:** fields the loader doesn't know are kept and warned about, never a crash, so new fields can be added any time. Missing fields get plain defaults. A place can have its own `personas/` folder (`docs/dev/places.md`); the repo's personas stay available.

The personality text goes first in the AI's instructions, then the fixed rules (the place's name, the time, "you can't change or move anything", short answers). The pages never get the personality text.

## The greeting
After the start press, the hub shows **"Good morning / afternoon / evening."** plus **one line of real news**, and the chat's first message is the same line. The news is built by the brain from real facts, never by the persona or the AI. It uses the first of these that applies:
1. **A step finished** today or yesterday (`(done YYYY-MM-DD)` in `docs/plan/current-focus.md`): "Step 5, Typed chat, was finished today."
2. **The calendar:** a date within two weeks from `calendar` in `config/place.yaml`: "The semester ends in 6 days."
3. **A busy day:** 10 or more commits yesterday, or today so far: "Yesterday was a busy day: 23 commits."

Otherwise the persona's `greeting` line. Where voice works, it's also spoken, with a hint how to talk (`docs/guides/voice.md` → "The spoken greeting": the time of day and the hint only, from a recording, never the news or this line). Later news (alerts, a device that dropped out, the budget running low) slots in at the top of that list (`src/lab_os/hub/greeting.py`).
