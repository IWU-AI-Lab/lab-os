"""The Wake Word page's clips and the verifier trained from them (quick job 99).

The builder says the wake word many times, in many tones (like a question, fast, slowly, quietly),
and talks for a while without it. The clips are kept in the place's `local/wake/<word>/` folder (not
in git): `word/*.wav` and `other/*.wav`, 16 kHz mono. "Train" fits the word's verifier on them
(`lab_os.ai.wake.Verifier`): the windows where the word model scored highest in each try of the
word, against every window of the other talk. The detector then also counts a lower score that the
verifier takes for the word (`lab_os.ai.wake`).

GET  /api/wake-word                     the words, with their clips and the last training
POST /api/wake-word/{word}/clip?kind=   a clip (raw 16-bit 16 kHz mono PCM): kind "word" or "other"
POST /api/wake-word/{word}/train        train the verifier; the result in plain words
POST /api/wake-word/{word}/clear        delete the word's clips and verifier

Only from the brain's computer, like Settings: the clips and the verifier are for its microphone.
"""

import asyncio
import json
import logging
import time
import uuid
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np
from aiohttp import web

from lab_os import config
from lab_os.ai.speech import RATE, wav_bytes
from lab_os.ai.wake import (
    PHRASES,
    SENSITIVITY,
    THRESHOLD,
    VERIFIED,
    VERIFY_FROM,
    Verifier,
    WakeDetector,
    WakeModels,
)
from lab_os.teleop.server import is_local

log = logging.getLogger(__name__)

KINDS = ("word", "other")
MAX_CLIP_S = {"word": 4.0, "other": 15.0}
MIN_CLIP_S = 0.5
NEED_WORD = 8  # tries of the word before Train
NEED_OTHER_S = 20.0  # seconds of other talk before Train
NEAR = 1  # the windows next to the best one count as the word too
FOLDS = 4  # the check: each quarter of the clips is held out once
PAD = np.zeros(RATE // 2, np.int16)  # half a second of quiet around each clip


def folder(word: str) -> Path:
    return config.local_dir() / "wake" / word


def _clips(word: str, kind: str) -> list[Path]:
    return sorted((folder(word) / kind).glob("*.wav"))


def _read(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16)


def _windows(models: WakeModels, word: str, pcm: np.ndarray) -> list[tuple[float, np.ndarray]]:
    """(score, window) of each 80 ms chunk of a clip, with the word model alone."""
    det = WakeDetector(models, word)
    det.verifier = None
    det.windows = []
    det.feed(np.concatenate([PAD, pcm, PAD]).tobytes())
    return det.windows


def best_score(models: WakeModels, word: str, pcm: np.ndarray) -> float:
    return max((s for s, _ in _windows(models, word, pcm)), default=0.0)


def _word_windows(wins: list[tuple[float, np.ndarray]]) -> np.ndarray:
    i = max(range(len(wins)), key=lambda k: wins[k][0])
    return np.stack([w for _, w in wins[max(0, i - NEAR) : i + NEAR + 1]])


def _heard(v: Verifier | None, wins, threshold: float) -> bool:
    """Would the detector count this clip (one chunk; patience 1)?"""
    for score, win in wins:
        if score >= threshold:
            return True
        if v is not None and score >= VERIFY_FROM and v.chance(win) >= VERIFIED:
            return True
    return False


def _seconds_heard(v: Verifier | None, wins, threshold: float) -> int:
    """How many seconds of a clip of other talk would wake it."""
    seconds = set()
    for k, (score, win) in enumerate(wins):
        if score >= threshold or (
            v is not None and score >= VERIFY_FROM and v.chance(win) >= VERIFIED
        ):
            seconds.add(k * 80 // 1000)
    return len(seconds)


def train(models: WakeModels, word: str, sensitivity: int = 9) -> dict:
    """Fit and save the word's verifier; check it on held-out clips. The check is the detector's
    rule at `sensitivity` (the threshold; one chunk is enough)."""
    threshold = SENSITIVITY.get(sensitivity, (THRESHOLD, 1))[0]
    pos = [_windows(models, word, _read(p)) for p in _clips(word, "word")]
    neg = [_windows(models, word, _read(p)) for p in _clips(word, "other")]
    pos, neg = [w for w in pos if w], [w for w in neg if w]
    other_s = sum(len(w) for w in neg) * 0.08
    if len(pos) < NEED_WORD or other_s < NEED_OTHER_S:
        raise ValueError(
            f"Record at least {NEED_WORD} tries of the word and {NEED_OTHER_S:.0f} s of other "
            f"talk first (now {len(pos)} tries and {other_s:.0f} s)."
        )

    def fit(ps, ns) -> Verifier:
        return Verifier.fit(
            np.concatenate([_word_windows(w) for w in ps]),
            np.concatenate([np.stack([x for _, x in w]) for w in ns]),
        )

    # the check: each try and each clip of other talk, judged by a verifier that didn't learn it
    word_before = word_now = other_before = other_now = 0
    for f in range(FOLDS):
        p_in = [w for k, w in enumerate(pos) if k % FOLDS != f]
        n_in = [w for k, w in enumerate(neg) if k % FOLDS != f] or neg
        v = fit(p_in, n_in)
        for w in pos[f::FOLDS]:
            word_before += _heard(None, w, threshold)
            word_now += _heard(v, w, threshold)
        if len(neg) > 1:
            for w in neg[f::FOLDS]:
                other_before += _seconds_heard(None, w, threshold)
                other_now += _seconds_heard(v, w, threshold)
    v = fit(pos, neg)
    v.save(models.verifier_path(word))
    result = {
        "ok": True,
        "word": word,
        "at": time.strftime("%Y-%m-%d %H:%M"),
        "sensitivity": sensitivity,
        "tries": len(pos),
        "word_before": word_before,
        "word_now": word_now,
        "other_s": round(other_s),
        "other_before": other_before,
        "other_now": other_now,
        "checked_other": len(neg) > 1,
    }
    (folder(word) / "training.json").write_text(json.dumps(result))
    log.info(
        'wake word: trained the verifier for "%s": %d of %d tries heard (was %d); '
        "other talk woke it in %d s of %d (was %d)",
        PHRASES[word][1],
        word_now,
        len(pos),
        word_before,
        other_now,
        round(other_s),
        other_before,
    )
    return result


def summary(word: str) -> dict:
    seconds = 0.0
    for p in _clips(word, "other"):
        with wave.open(str(p), "rb") as w:
            seconds += w.getnframes() / RATE
    trained = folder(word) / "training.json"
    try:
        last = json.loads(trained.read_text()) if trained.is_file() else None
    except ValueError:
        last = None
    return {
        "id": word,
        "phrase": PHRASES[word][1],
        "word_clips": len(_clips(word, "word")),
        "other_s": round(seconds),
        "trained": last if (folder(word) / "verifier.npz").is_file() else None,
    }


def add_routes(
    app: web.Application,
    models: Callable[[web.Application], WakeModels],
    active: Callable[[web.Application], str],
) -> None:
    """The Wake Word page's API. `models`: the brain's wake models; `active`: the persona's word."""

    def word_of(request: web.Request) -> str:
        if not is_local(request):
            raise web.HTTPForbidden(text="Record wake word clips on the brain's computer only.")
        word = request.match_info["word"]
        if word not in PHRASES:
            raise web.HTTPNotFound(text=f"There's no wake word {word!r}.")
        return word

    async def get_words(request: web.Request) -> web.Response:
        words = await asyncio.to_thread(lambda: [summary(w) for w in PHRASES])
        return web.json_response(
            {
                "active": active(request.app),
                "words": words,
                "need_word": NEED_WORD,
                "need_other_s": NEED_OTHER_S,
                "here": is_local(request),
            }
        )

    async def post_clip(request: web.Request) -> web.Response:
        word = word_of(request)
        kind = request.query.get("kind", "")
        if kind not in KINDS:
            raise web.HTTPBadRequest(text='kind is "word" or "other"')
        body = await request.read()
        pcm = np.frombuffer(body[: len(body) // 2 * 2], np.int16)
        seconds = len(pcm) / RATE
        if not MIN_CLIP_S <= seconds <= MAX_CLIP_S[kind] + 0.5:
            raise web.HTTPBadRequest(text=f"A clip is {MIN_CLIP_S} to {MAX_CLIP_S[kind]} s long.")

        def keep() -> float:
            name = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.wav"
            path = folder(word) / kind / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(wav_bytes(pcm.tobytes()))
            return best_score(models(request.app), word, pcm)

        score = await asyncio.to_thread(keep)
        return web.json_response({"ok": True, "score": round(score, 2)} | summary(word))

    async def post_train(request: web.Request) -> web.Response:
        word = word_of(request)
        try:
            level = int(request.query.get("sensitivity", "9"))
        except ValueError:
            level = 9
        try:
            out = await asyncio.to_thread(train, models(request.app), word, level)
        except ValueError as e:
            return web.json_response({"ok": False, "message": str(e)}, status=400)
        return web.json_response(out | {"summary": summary(word)})

    async def post_clear(request: web.Request) -> web.Response:
        word = word_of(request)

        def clear() -> None:
            for kind in KINDS:
                for p in _clips(word, kind):
                    p.unlink()
            for name in ("verifier.npz", "training.json"):
                (folder(word) / name).unlink(missing_ok=True)

        await asyncio.to_thread(clear)
        log.info('wake word: the clips and the verifier for "%s" were deleted', PHRASES[word][1])
        return web.json_response({"ok": True} | summary(word))

    app.router.add_get("/api/wake-word", get_words)
    app.router.add_post("/api/wake-word/{word}/clip", post_clip)
    app.router.add_post("/api/wake-word/{word}/train", post_train)
    app.router.add_post("/api/wake-word/{word}/clear", post_clear)
