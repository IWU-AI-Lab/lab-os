"""Capital letters in content text (quick job 53, done in quick job 153). docs/design/DESIGN.md:
labels are small CAPS, content is normal case, so a sentence and a status word start with a
capital letter ("Connected", not "connected"). Names of commands, files, poses and settings stay
as they are.

The test reads the pages where it can: the words written in the HTML, and the words the scripts put
on a status pill or into an element's text. Words that a page builds from data are not checked."""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "src" / "lab_os"
PAGES = sorted([*WEB.glob("hub/web/*.html"), *WEB.glob("teleop/web/*.html")])
SCRIPTS = sorted(
    p
    for p in [*WEB.glob("hub/web/**/*.js"), *WEB.glob("teleop/web/**/*.js"), *WEB.glob("web/*.js")]
)

# a name that stays as it is: lab-os, an axis, a code name or a file (has _ . / = : #), a number
NAME = re.compile(r"^([xyz]$|lab-os|e\.g\.|i\.e\.|iPhone|xArm|[a-z0-9_-]+[_./=:#]|\d)")
NOT_TEXT = {"script", "style", "code", "kbd", "pre", "samp", "textarea", "svg"}
INLINE = {"b", "i", "em", "strong", "a", "small", "span", "abbr", "sup", "sub", "u", "mark", "kbd"}
INLINE |= {"code", "label"}
EMPTY = {"br", "img", "input", "meta", "link", "hr", "source", "wbr", "use", "path", "circle"}
EMPTY |= {"line", "rect"}


class FirstWords(HTMLParser):
    """The first words of each block of text (a sentence's start), with their line."""

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.fresh = [True]  # one per block: no words seen in it yet
        self.found: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in EMPTY:
            return
        self.stack.append(tag)
        if tag not in INLINE:
            self.fresh.append(True)
        elif dict(attrs).get("id"):
            self.fresh[-1] = False  # a script fills it: the words after it go on its sentence

    def handle_endtag(self, tag):
        if tag in EMPTY:
            return
        while self.stack:
            top = self.stack.pop()
            if top not in INLINE and len(self.fresh) > 1:
                self.fresh.pop()
            if top == tag:
                break

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        first, self.fresh[-1] = self.fresh[-1], False
        if first and not NOT_TEXT & set(self.stack):
            self.found.append((self.getpos()[0], text))


def lowercase(text: str) -> bool:
    return bool(text) and text[0].islower() and not NAME.match(text)


def test_the_pages_start_their_words_with_a_capital_letter():
    bad = []
    for page in PAGES:
        parser = FirstWords()
        parser.feed(page.read_text())
        bad += [f"{page.name}:{n}: {t[:50]!r}" for n, t in parser.found if lowercase(t)]
    assert not bad, "content text starts with a small letter:\n" + "\n".join(bad)


# what a script shows: the words of a status pill, and the words put into an element's text
PILL = re.compile(r"setPill\([^,()]+(?:\([^()]*\))?,\s*[\"`]([^\"`$]*)")
SHOWN = re.compile(r"\.textContent\s*=\s*([^;]+)")
LITERAL = re.compile(r"\"([^\"\\]*)\"|`([^`\\$]*)`")
COMPARED = re.compile(r"[!=]==?\s*\"[^\"]*\"")  # m.state === "loading": not shown
CALLED = re.compile(r"[\w$.]+\(\s*\"[^\"]*\"\s*\)")  # $("depth").checked: not shown
INSIDE = re.compile(r"\$\{[^{}]*\}")  # a template's ${…}: its words go inside a sentence
MID_SENTENCE = "in a sentence"  # a comment on the line: the words go inside a sentence on purpose


def shown_words(rhs: str) -> list[str]:
    """The words an assignment shows, without what goes inside a template or is only compared."""
    while INSIDE.search(rhs):
        rhs = INSIDE.sub("", rhs)
    rhs = CALLED.sub("", COMPARED.sub("", rhs))
    return [a if a is not None else b for a, b in LITERAL.findall(rhs)]


def test_the_scripts_show_words_with_a_capital_letter():
    bad = []
    for script in [*SCRIPTS, *PAGES]:
        for n, line in enumerate(script.read_text().splitlines(), 1):
            if line.lstrip().startswith("//") or MID_SENTENCE in line:
                continue
            words = [m.group(1) for m in PILL.finditer(line)]
            for m in SHOWN.finditer(line):
                words += shown_words(m.group(1))
            bad += [f"{script.name}:{n}: {w[:50]!r}" for w in words if lowercase(w)]
    assert not bad, "a script shows words that start with a small letter:\n" + "\n".join(bad)


def test_the_rule_is_written_down():
    """Future sessions keep it: the rule is in AGENTS.md and DESIGN.md, with this test named."""
    root = WEB.parents[1]
    for doc in ("AGENTS.md", "docs/design/DESIGN.md"):
        text = (root / doc).read_text()
        assert "test_content_case.py" in text, doc


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node isn't installed")
def test_the_shared_words():
    """/web/words.js: one name for one thing on every page (quick job 153)."""
    words = (WEB / "web" / "words.js").as_uri()
    script = (
        f"import({json.dumps(words)}).then(m => console.log(JSON.stringify(["
        "['shoulder_pan', 'wrist_roll', 'gripper'].map(m.jointLabel),"
        "m.held(true), m.held(false, 'the clutch'), m.cap('connected')])))"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    joints, held, quiet, word = json.loads(out.stdout)
    assert joints == ["Shoulder Pan", "Wrist Roll", "Gripper"]
    assert held["text"] == quiet["text"] == "Held still" and "Let go of the grip" in held["why"]
    assert word == "Connected"
