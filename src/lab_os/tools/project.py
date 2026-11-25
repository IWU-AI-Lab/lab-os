"""The project helper's read tools (focus step 6): the docs, git, the device list.

Plain logic with no MCP in it; lab_os.tools.mcp_server offers these as MCP tools (read tier), and
the hub's chat uses the same ones. Nothing here writes, runs a fetch or opens a device.

The docs are `docs/**/*.md` plus README, CHANGELOG, SAFETY and AGENTS at the top, `docs/design/`
included (the design stopped being a surprise on 2026-11-12). A doc's name is its path under docs/
without `.md` ("plan/current-focus"); its last part alone ("current-focus") works too when only one
doc has it.
"""

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from lab_os.devices import Registry, load_registry
from lab_os.hub.project import project_summary
from lab_os.venues import Venue

TOP_DOCS = ("README.md", "CHANGELOG.md", "SAFETY.md", "AGENTS.md")
MAX_CHARS = 12_000  # one doc or section per call (the AI pays per token)
MAX_HITS = 30
GIT_TIMEOUT_S = 10

_HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")


class NotFound(LookupError):
    """Unknown doc or section; the message lists what there is."""


def _git(repo: Path, *args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def headings(text: str) -> list[str]:
    out, fence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        m = None if fence else _HEADING.match(line)
        if m:
            out.append(m.group(2))
    return out


def section_of(text: str, wanted: str) -> str | None:
    """The section under the first heading containing `wanted` (any case), down to the next
    heading of the same or a higher level."""
    lines, start, level, fence = text.splitlines(), None, 0, False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            fence = not fence
        m = None if fence else _HEADING.match(line)
        if not m:
            continue
        if start is None and wanted.lower() in m.group(2).lower():
            start, level = i, len(m.group(1))
        elif start is not None and len(m.group(1)) <= level:
            return "\n".join(lines[start:i]).strip()
    return "\n".join(lines[start:]).strip() if start is not None else None


class ProjectTools:
    def __init__(
        self,
        repo: Path,
        venue: Venue | None = None,
        registry: Callable[[], Registry] = load_registry,
    ):
        self.repo = repo
        self.venue = venue
        self._registry = registry
        # the brain's live device list (quick job 109), set by the brain; None elsewhere
        self.live: Callable[[], list[dict]] | None = None

    # ---------- docs ----------

    def _docs(self) -> dict[str, Path]:
        """name → file: "plan/current-focus" → docs/plan/current-focus.md, "README" → README.md."""
        docs = {}
        root = self.repo / "docs"
        for path in sorted(root.rglob("*.md")):
            docs[path.relative_to(root).with_suffix("").as_posix()] = path
        for name in TOP_DOCS:
            if (self.repo / name).is_file():
                docs[Path(name).stem] = self.repo / name
        return docs

    def _find(self, name: str) -> tuple[str, Path]:
        """By full name ("plan/ideas"), or by its last part ("ideas") when only one doc has it."""
        key = name.strip().removeprefix("docs/").removesuffix(".md").lower()
        docs = self._docs()
        for doc, path in docs.items():
            if doc.lower() == key:
                return doc, path
        short = [(doc, path) for doc, path in docs.items() if doc.lower().split("/")[-1] == key]
        if len(short) == 1:
            return short[0]
        raise NotFound(f"no doc {name!r}; there are: {', '.join(docs)}")

    def list_docs(self) -> dict:
        out = []
        for name, path in self._docs().items():
            text = path.read_text()
            title = next(iter(headings(text)), name)
            out.append({"name": name, "file": str(path.relative_to(self.repo)), "title": title})
        return {"docs": out}

    def read_doc(self, name: str, section: str | None = None) -> dict:
        doc, path = self._find(name)
        text = path.read_text()
        if section:
            part = section_of(text, section)
            if part is None:
                raise NotFound(f"{doc} has no section {section!r}; sections: {headings(text)}")
            text = part
        truncated = len(text) > MAX_CHARS
        result = {
            "name": doc,
            "file": str(path.relative_to(self.repo)),
            "section": section,
            "text": text[:MAX_CHARS],
            "truncated": truncated,
        }
        if truncated:
            result["note"] = "Cut off: ask for one section (see sections)."
            result["sections"] = headings(path.read_text())
        return result

    def search_docs(self, text: str) -> dict:
        """Lines containing `text` (any case), with the doc and the heading they're under."""
        needle = text.strip().lower()
        if len(needle) < 2:
            raise NotFound("search for at least 2 characters")
        hits = []
        for name, path in self._docs().items():
            heading, fence = None, False
            for n, line in enumerate(path.read_text().splitlines(), 1):
                if line.startswith("```"):
                    fence = not fence
                m = None if fence else _HEADING.match(line)
                if m:
                    heading = m.group(2)
                if needle in line.lower():
                    snippet = line.strip()
                    hits.append({"doc": name, "line": n, "heading": heading, "text": snippet[:300]})
                    if len(hits) >= MAX_HITS:
                        return {"hits": hits, "more": True}
        return {"hits": hits, "more": False}

    def project_status(self) -> dict:
        """The current focus: its name, every step (done or not), the next one."""
        summary = project_summary(self.repo / "docs" / "plan" / "current-focus.md")
        summary.pop("available", None)
        summary["read_more"] = "read_doc('current-focus', section=...) for a step's details"
        return summary

    # ---------- git ----------

    def git_status(self) -> dict:
        """Branch, how far it is from its remote (as of the last fetch: nothing is fetched), the
        changed files, the last commit."""
        out = _git(self.repo, "status", "--porcelain=v1", "--branch")
        if out is None:
            return {"available": False}
        lines = out.splitlines()
        head = lines[0][3:] if lines and lines[0].startswith("## ") else ""
        last = _git(self.repo, "log", "-1", "--format=%h %cs %s") or ""
        return {
            "available": True,
            "branch": head,
            "changed": [line for line in lines[1:]][:50],
            "last_commit": last.strip(),
        }

    def git_log(self, count: int = 15, path: str | None = None) -> dict:
        """Recent commits on the current branch (newest first): hash, date, author, subject."""
        count = max(1, min(50, int(count)))
        args = ["log", f"-{count}", "--format=%h%x09%cs%x09%an%x09%s"]
        if path:
            if path.startswith("-") or ".." in Path(path).parts:
                raise NotFound(f"not a path in the repo: {path!r}")
            args += ["--", path]
        out = _git(self.repo, *args)
        if out is None:
            return {"available": False}
        commits = []
        for line in out.splitlines():
            h, day, author, subject = (line.split("\t") + ["", "", "", ""])[:4]
            commits.append({"hash": h, "date": day, "author": author, "subject": subject})
        return {"available": True, "commits": commits}

    # ---------- devices ----------

    def list_devices(self) -> dict:
        """The place's device list: name, kind, off limits, borrowed (another project's, drivable
        with AGENTS.md's rules), active in this venue, notes. In the brain (quick job 109), also
        what is connected now (the live list, looked at every 2 s): `connected` for each device,
        `motor_power` for the arms the brain drives, `other_connected` for the USB devices and
        cameras devices.yaml doesn't know, and `screens` with the hub open."""
        active = set(self.venue.active_devices) if self.venue else set()
        live = self.live() if self.live else None
        now = {d["name"]: d for d in live or () if d["connected"]}
        devices = []
        for d in self._registry().devices.values():
            entry = {
                "name": d.name,
                "kind": d.kind,
                "off_limits": d.off_limits,
                "borrowed": d.borrowed,
                "active_in_venue": d.name in active,
                "notes": " ".join(d.notes.split()),
            }
            if live is not None and d.kind != "fake":
                here = now.get(d.name) or next(
                    (x for x in now.values() if d.name in x.get("names", ())), None
                )
                entry["connected"] = here is not None
                if here and here.get("driven"):
                    entry["motor_power"] = here.get("power") or "not known yet"
                    if here.get("problem"):
                        entry["problem"] = here["problem"]
            devices.append(entry)
        out = {"venue": self.venue.name if self.venue else None, "devices": devices}
        if live is not None:
            out["other_connected"] = [
                {"name": d["name"], "kind": d["kind"], "what": d.get("what", "")}
                for d in now.values()
                if not d.get("known") and d["kind"] != "screen"
            ]
            out["screens"] = [d["name"] for d in now.values() if d["kind"] == "screen"]
            out["how"] = (
                "connected: plugged in or on the network now. motor_power only for the arms the "
                "brain drives (the others: not known; their port is not opened)."
            )
        return out
