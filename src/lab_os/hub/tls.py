"""The hub over HTTPS for phones (quick job 124): a phone's browser gives the microphone only to a
secure page, and an iPhone has no "Insecure origins treated as secure" flag.

The brain makes its own small certificate authority once (`local/tls/lab-os-ca.crt`, ten years)
and with it a certificate for this computer's names and addresses (`hub.crt`, 800 days: an iPhone
trusts no longer one). The hub is then also at `https://<address>:8443/`. When the addresses change,
the brain makes a new `hub.crt` with the same authority, so a phone that trusts it once keeps
trusting it.

- **Android** (Chrome): open the https address and accept the warning once ("Advanced" →
  "Proceed").
- **iPhone** (Safari): accepting the warning is not enough, because Safari's WebSockets do not
  take that exception. Install the authority once: open `http://<address>:8080/lab-os-ca.crt`,
  install the profile, then turn on full trust (Settings → General → About → Certificate Trust
  Settings).

Like mkcert (the usual tool for this), but made with `cryptography`, which lab-os already has, so
nothing more to install. The key files stay in the place's `local/` folder (not in git).
"""

import datetime
import ipaddress
import logging
import socket
import ssl
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from lab_os import config

log = logging.getLogger(__name__)

FOLDER = "tls"
CA_CERT, CA_KEY = "lab-os-ca.crt", "lab-os-ca.key"
HUB_CERT, HUB_KEY = "hub.crt", "hub.key"
CA_DAYS = 3650
HUB_DAYS = 800  # an iPhone refuses a trusted server certificate valid longer than 825 days
RENEW_DAYS = 30  # a hub certificate this close to its end is made again
DEFAULT_PORT = 8443


def tls_dir() -> Path:
    return config.local_dir() / FOLDER


def this_computer() -> tuple[list[str], list[str]]:
    """(names, IP addresses) a phone may use for this computer: its host name (and `.local`),
    `localhost`, and every IPv4 address it has (found without sending anything)."""
    host = socket.gethostname().split(".")[0].lower()
    names = sorted({"localhost", host, f"{host}.local"} - {""})
    ips = {"127.0.0.1"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(str(info[4][0]))
    except OSError:
        pass
    # the address the default route leaves from (a UDP "connect" sends nothing)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))
            ips.add(s.getsockname()[0])
        except OSError:
            pass
    return names, sorted(ips)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _write_key(path: Path, key) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def _load_key(path: Path):
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def _authority(folder: Path) -> tuple[x509.Certificate, object]:
    """The place's certificate authority: read, or made the first time."""
    crt, key = folder / CA_CERT, folder / CA_KEY
    if crt.exists() and key.exists():
        return x509.load_pem_x509_certificate(crt.read_bytes()), _load_key(key)
    folder.mkdir(parents=True, exist_ok=True)
    k = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "lab-os"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"lab-os on {socket.gethostname()}"),
        ]
    )
    now = _now()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(k.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(k.public_key()), critical=False)
        .sign(k, hashes.SHA256())
    )
    _write_key(key, k)
    crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    log.info("https: made the place's certificate authority (%s)", config.shown_path(crt))
    return cert, k


def _covers(cert: x509.Certificate, names: list[str], ips: list[str]) -> bool:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return False
    has_names = set(san.get_values_for_type(x509.DNSName))
    has_ips = {str(a) for a in san.get_values_for_type(x509.IPAddress)}
    fresh = cert.not_valid_after_utc - _now() > datetime.timedelta(days=RENEW_DAYS)
    return fresh and set(names) <= has_names and set(ips) <= has_ips


def ensure_certificate(
    folder: Path | None = None, names: list[str] | None = None, ips: list[str] | None = None
) -> tuple[Path, Path]:
    """(hub.crt, hub.key) for this computer's names and addresses: the ones there, or new ones
    signed by the place's authority when an address is missing or the end is near."""
    folder = folder or tls_dir()
    if names is None or ips is None:
        found_names, found_ips = this_computer()
        names, ips = names or found_names, ips or found_ips
    ca, ca_key = _authority(folder)
    crt, key = folder / HUB_CERT, folder / HUB_KEY
    if (
        crt.exists()
        and key.exists()
        and _covers(x509.load_pem_x509_certificate(crt.read_bytes()), names, ips)
    ):
        return crt, key
    k = ec.generate_private_key(ec.SECP256R1())
    now = _now()
    alt = [x509.DNSName(n) for n in names] + [x509.IPAddress(ipaddress.ip_address(a)) for a in ips]
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, names[0])]))
        .issuer_name(ca.subject)
        .public_key(k.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=HUB_DAYS))
        .add_extension(x509.SubjectAlternativeName(alt), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.public_key()), critical=False
        )
        .sign(ca_key, hashes.SHA256())
    )
    _write_key(key, k)
    crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    log.info("https: made the hub's certificate for %s", ", ".join([*names, *ips]))
    return crt, key


def server_context(folder: Path | None = None) -> ssl.SSLContext:
    """The HTTPS site's settings, with the hub's certificate (made when needed)."""
    crt, key = ensure_certificate(folder)
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(crt, key)
    return ctx


def authority_file(folder: Path | None = None) -> Path:
    """The authority's certificate (no key), for a phone to install; made when needed."""
    folder = folder or tls_dir()
    _authority(folder)
    return folder / CA_CERT
