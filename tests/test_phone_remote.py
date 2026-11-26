"""The phone as a remote for the assistant (quick job 124): the remote page for phones, the hub over
HTTPS with the brain's own certificate, and the assistant's tool that shows a page on the screens
someone names (else on the brain's own computer)."""

import json
import ssl
from types import SimpleNamespace

from cryptography import x509
from test_hub_devices import next_of, page, settle  # same folder (pytest puts it on the path)
from test_hub_server import make_app

from lab_os import cli
from lab_os.hub import tls
from lab_os.hub.screens import SHOW, ScreensDesk
from lab_os.hub.server import BRAIN, HUB_DEVICES, PAGES

IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like "
    "Gecko) Version/18.6 Mobile/15E148 Safari/604.1"
)
ANDROID = (
    "Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0 Mobile Safari/537.36"
)
TABLET = (
    "Mozilla/5.0 (Linux; Android 13; SM-X200) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0 Safari/537.36"
)
QUEST = (
    "Mozilla/5.0 (X11; Linux x86_64; Quest 3) AppleWebKit/537.36 (KHTML, like Gecko) "
    "OculusBrowser/40.0 Chrome/138.0 Mobile VR Safari/537.36"
)


# ---------- the certificate ----------


def _san(path):
    cert = x509.load_pem_x509_certificate(path.read_bytes())
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    return (
        cert,
        set(san.get_values_for_type(x509.DNSName)),
        {str(a) for a in san.get_values_for_type(x509.IPAddress)},
    )


def test_the_brain_makes_a_certificate_for_its_addresses(tmp_path):
    crt, key = tls.ensure_certificate(tmp_path, ["localhost", "brain"], ["127.0.0.1", "10.0.0.5"])
    cert, names, ips = _san(crt)
    assert names == {"localhost", "brain"} and ips == {"127.0.0.1", "10.0.0.5"}
    ca = x509.load_pem_x509_certificate((tmp_path / tls.CA_CERT).read_bytes())
    cert.verify_directly_issued_by(ca)  # signed by the place's authority
    days = (cert.not_valid_after_utc - cert.not_valid_before_utc).days
    assert days <= 825  # an iPhone trusts no longer one
    assert oct(key.stat().st_mode & 0o777) == "0o600"
    # the same addresses: the same certificate
    before = crt.read_bytes()
    tls.ensure_certificate(tmp_path, ["localhost", "brain"], ["127.0.0.1"])
    assert crt.read_bytes() == before
    # a new address: a new certificate, from the same authority (a phone keeps trusting it)
    ca_before = (tmp_path / tls.CA_CERT).read_bytes()
    tls.ensure_certificate(tmp_path, ["localhost", "brain"], ["127.0.0.1", "10.0.0.9"])
    cert, _, ips = _san(crt)
    assert "10.0.0.9" in ips and crt.read_bytes() != before
    assert (tmp_path / tls.CA_CERT).read_bytes() == ca_before
    cert.verify_directly_issued_by(ca)


def test_the_https_settings_load(tmp_path):
    assert isinstance(tls.server_context(tmp_path), ssl.SSLContext)
    names, ips = tls.this_computer()
    assert "localhost" in names and "127.0.0.1" in ips


def test_https_only_when_other_computers_can_reach_the_brain(monkeypatch):
    monkeypatch.setattr(tls, "server_context", lambda: "ctx")
    args = SimpleNamespace(https_port=8443, host="127.0.0.1")
    assert cli._https(args) is None
    args.host = "0.0.0.0"
    assert cli._https(args) == (8443, "ctx")
    args.https_port = 0
    assert cli._https(args) is None
    assert "https://<this computer's IP address>:8443/" in cli._banner(8080, "0.0.0.0", 0, 8443)


# ---------- the page ----------


async def test_a_phone_gets_the_remote(aiohttp_client):
    client = await aiohttp_client(make_app())

    async def front(agent, path="/"):
        return await (await client.get(path, headers={"User-Agent": agent})).text()

    assert "/hub/remote.js" in await front(IPHONE)
    assert "/hub/remote.js" in await front(ANDROID)
    assert "/hub/remote.js" not in await front(TABLET)  # a tablet gets the hub
    assert "/hub/remote.js" not in await front(IPHONE, "/?hub=1")  # the whole hub, asked for
    assert "/hub/remote.js" not in await front(QUEST)  # the headset's start page
    assert "/hub/remote.js" in await front(TABLET, "/remote")
    js = await (await client.get("/hub/remote.js")).text()
    assert "pages: null" in js  # the phone shows no pages: they open on a screen
    assert (await (await client.get("/api/remote")).json()) == {"https_port": 0}
    assert "/remote" in {p[0] for p in PAGES}


async def test_the_certificate_authority_downloads(aiohttp_client, monkeypatch, tmp_path):
    monkeypatch.setattr(tls, "tls_dir", lambda: tmp_path)
    client = await aiohttp_client(make_app())
    r = await client.get("/lab-os-ca.crt")
    assert r.status == 200 and r.headers["Content-Type"] == "application/x-x509-ca-cert"
    body = await r.read()
    assert b"BEGIN CERTIFICATE" in body and b"PRIVATE" not in body


# ---------- the assistant shows a page on the named screens ----------


async def test_the_assistant_opens_a_page_on_the_screen_named(aiohttp_client):
    app = make_app()
    client = await aiohttp_client(app)
    desk, _ = await page(client, "desk")  # on the brain's computer (the test client is local)
    newline, _ = await page(client, "newline")
    names = {t["function"]["name"] for t in app[BRAIN].chat.actions.tools(False)}
    assert SHOW in names  # from every screen, also a phone
    tool = next(t for t in app[BRAIN].chat.actions.tools(False) if t["function"]["name"] == SHOW)
    assert "newline" in tool["function"]["description"]
    desk_tools = ScreensDesk(lambda: app[HUB_DEVICES])

    async def call(**args):
        out, events = await app[BRAIN].chat.actions.call(SHOW, False, json.dumps(args))
        assert events == []
        return json.loads(out)["result"]

    said = await call(page="system", screens=["newline"])
    assert said == "System Diagram is open on newline."
    msg = await next_of(newline, "open")
    assert msg["module"] == "system" and msg["from"] == "assistant"
    # two screens at once
    said = await call(page="spend", screens=["desk", "newline"])
    assert "AI Spend is open on desk." in said
    assert (await next_of(desk, "open"))["module"] == "spend"
    assert (await next_of(newline, "open"))["module"] == "spend"
    # no screen named: the brain's own computer
    await desk_tools.show("hub", "desk")
    await next_of(desk, "close")
    await settle(client)
    said = await call(page="monitor")
    assert said == "Monitor is open on desk."
    assert (await next_of(desk, "open"))["module"] == "monitor"
    # back to the hub; a screen that isn't there; a page that doesn't open on a screen
    assert await call(page="hub", screens=["newline"]) == "Back to the hub on newline."
    assert (await next_of(newline, "close")) == {"type": "close"}
    assert "Error: not on quest" in await call(page="system", screens=["quest"])
    assert "isn't a page" in await call(page="nope", screens=["newline"])
    await desk.close()
    await newline.close()
