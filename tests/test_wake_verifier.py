# ruff: noqa: F811 (`key` is a fixture from test_voice, used as an argument)
"""Quick job 99: the wake word's verifier (a small model trained on one speaker's tries of the
word), the Wake Word page's clips and training, and the log of each missed second."""

import asyncio
import logging
import time

import numpy as np
import pytest
from test_voice import key, voice_app  # noqa: F401 (key is a fixture)
from test_wake import events_until, noisy, pcm, pieces, stream

from lab_os.ai.wake import FEATURES, VERIFY_FROM, Verifier, WakeDetector, WakeModels

PAD = b"\x00\x00" * 16000  # a second of quiet: past the detector's warm-up


@pytest.fixture(scope="module")
def models():
    return WakeModels()


class Always:
    """A verifier that always says the same."""

    def __init__(self, chance: float):
        self.value = chance

    def chance(self, features):
        assert features.shape == (FEATURES, 96)
        return self.value


def fired(det: WakeDetector, data: bytes) -> bool:
    heard = False
    for p in pieces(data):
        det.feed(p)
        heard = heard or det.fired
    return heard


def test_the_verifier_learns_and_keeps(tmp_path):
    rng = np.random.default_rng(0)
    pos = rng.normal(1.0, 1.0, (30, FEATURES, 96))
    neg = rng.normal(-1.0, 1.0, (300, FEATURES, 96))
    v = Verifier.fit(pos, neg)
    assert (v.chance(pos) > 0.5).all() and (v.chance(neg) < 0.5).all()
    path = tmp_path / "w" / "verifier.npz"
    v.save(path)
    again = Verifier.load(path)
    assert again.chance(pos[0]) == pytest.approx(v.chance(pos[0]))


def test_a_low_score_wakes_only_when_the_verifier_says_so(models):
    # TARS on macOS's voice scores about 0.42: under the 0.5 of sensitivity 5, over VERIFY_FROM
    data = PAD + pcm("tars") + PAD
    plain = WakeDetector(models, "tars", sensitivity=5)
    assert not fired(plain, data)
    yes = WakeDetector(models, "tars", sensitivity=5)
    yes.verifier = Always(0.9)
    assert fired(yes, data) and yes.threshold > VERIFY_FROM
    no = WakeDetector(models, "tars", sensitivity=5)
    no.verifier = Always(0.1)
    assert not fired(no, data)
    # quiet never asks it (the score stays under VERIFY_FROM)
    quiet = WakeDetector(models, "tars", sensitivity=5)
    quiet.verifier = Always(0.9)
    assert not fired(quiet, PAD * 3)


def tries(n: int) -> list[bytes]:
    """The word in n "tones": louder, quieter, a little noise (as a speaker's tries)."""
    return [noisy("tars", 0.6 + 0.1 * k, 50 + 30 * k, k) for k in range(n)]


async def test_record_and_train_on_the_page(aiohttp_client, aiohttp_server, key, tmp_path):
    from lab_os import config

    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    page = await client.get("/wake-word")
    assert page.status == 200 and "Wake Word" in await page.text()
    first = await (await client.get("/api/wake-word")).json()
    assert [w["id"] for w in first["words"]][0] == "hey_jarvis" and first["active"] == "hey_jarvis"

    # too few clips: a sentence, no verifier
    r = await client.post("/api/wake-word/tars/train")
    assert r.status == 400 and "Record at least" in (await r.json())["message"]
    bad = await client.post("/api/wake-word/tars/clip?kind=word", data=b"\x00\x00" * 100)
    assert bad.status == 400  # too short
    assert (await client.post("/api/wake-word/nope/clip?kind=word", data=PAD)).status == 404

    for clip in tries(8):
        r = await client.post("/api/wake-word/tars/clip?kind=word", data=clip)
        assert r.status == 200
        assert 0.0 <= (await r.json())["score"] <= 1.0
    other = noisy("not_jarvis", 1.0, 200, 9)
    for _ in range(6):  # about 4 s each: more than 20 s
        r = await client.post("/api/wake-word/tars/clip?kind=other", data=other[: 16000 * 2 * 4])
        assert r.status == 200
    got = await r.json()
    assert got["word_clips"] == 8 and got["other_s"] >= 20

    r = await client.post("/api/wake-word/tars/train?sensitivity=5")
    out = await r.json()
    assert r.status == 200 and out["ok"] and out["tries"] == 8
    assert out["word_now"] >= out["word_before"]
    path = config.local_dir() / "wake" / "tars" / "verifier.npz"
    assert path.is_file()
    assert out["summary"]["trained"]["tries"] == 8

    # the brain's detector uses it: the tries now wake it at sensitivity 5
    models = WakeModels()
    det = WakeDetector(models, "tars", sensitivity=5)
    assert det.verifier is not None and fired(det, PAD + tries(8)[3] + PAD)
    assert not fired(WakeDetector(models, "tars", sensitivity=5), PAD + other + PAD)

    r = await client.post("/api/wake-word/tars/clear")
    assert (await r.json())["word_clips"] == 0 and not path.exists()


async def test_only_the_brains_computer_records(aiohttp_client, aiohttp_server, key, tmp_path):
    from lab_os.hub import wake_clips

    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    orig = wake_clips.is_local
    wake_clips.is_local = lambda request: False
    try:
        r = await client.post("/api/wake-word/tars/clip?kind=word", data=PAD)
        assert r.status == 403
    finally:
        wake_clips.is_local = orig


async def test_a_missed_second_is_logged(aiohttp_client, aiohttp_server, key, tmp_path, caplog):
    app, _, _ = await voice_app(aiohttp_server, tmp_path)
    client = await aiohttp_client(app)
    ws = await client.ws_connect("/ws/voice?device=desk")
    await ws.send_json({"type": "wake", "on": True, "sensitivity": 1})  # takes 0.8
    await events_until(ws, {"wake_on"}, timeout=20)
    with caplog.at_level(logging.INFO, logger="lab_os.hub.voice"):
        # other talk, then quiet, sent over more than a second
        await stream(ws, PAD + noisy("not_jarvis", 1.0, 30, 1))
        t0 = time.monotonic()
        while 'desk missed "hey Jarvis"? best' not in caplog.text and time.monotonic() - t0 < 5:
            await ws.send_bytes(b"\x00\x00" * 800)
            await asyncio.sleep(0.05)
    assert 'desk missed "hey Jarvis"? best' in caplog.text, caplog.text
    assert "it takes 0.80 at sensitivity 1" in caplog.text
    await ws.close()
