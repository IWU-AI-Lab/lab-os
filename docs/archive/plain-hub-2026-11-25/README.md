# The plain hub (archived 2026-11-25, quick job 131)

The first hub (`index.html`, `hub.js`, `hub.css`). It was at `/` while the theme said `hub.look: plain`. Since quick job 131, `/` shows the designed hub (`src/lab_os/hub/web/design.html`), `/design` goes to `/`, and `hub.look` is gone.

These files do not run from here. They import `/web/*.js` files that have changed since.

What only the plain hub had, and where it went:
- The setting "Typing Anywhere Goes to the Ask Line" (`hub.type_to_chat`). The designed hub did not read it. Now it does.
- The "I heard you" chime (`voice.chime()` in `src/lab_os/web/voice.js`). The designed hub and VR play their own listening sound. The chime was removed.
- The `look` field in the hub page's `hello` to the brain (`docs/dev/protocol.md`). Nothing read it. It was removed.
