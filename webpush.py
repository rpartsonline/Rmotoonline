"""Pošiljanje potisnih obvestil (Web Push) brez zunanjih knjižnic.

Uporablja samo `cryptography`, ki ima pripravljene namestitvene pakete za vse
različice Pythona. Knjižnica `pywebpush` potegne za sabo `http-ece`, ki se z
novejšim setuptools ne zgradi več in bi lahko podrl namestitev na strežniku.

Standardi: RFC 8291 (šifriranje), RFC 8188 (aes128gcm), RFC 8292 (VAPID).
"""
import base64
import hashlib
import hmac
import json
import os
import struct
import time
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils as asym_utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes


def b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64d(s: str) -> bytes:
    s = s.strip().replace("-", "+").replace("_", "/")
    return base64.b64decode(s + "=" * (-len(s) % 4))


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    """HKDF s SHA-256 (RFC 5869). Dolžina nikoli ne presega 32 bajtov."""
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:length]


# ── Ključi VAPID ─────────────────────────────────────────────────────────────

def generate_vapid_keys():
    """Ustvari par ključev. Javni gre v brskalnik, zasebni ostane na strežniku."""
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return b64e(pub), b64e(priv.private_numbers().private_value.to_bytes(32, "big"))


def _load_private(priv_b64: str):
    return ec.derive_private_key(int.from_bytes(b64d(priv_b64), "big"), ec.SECP256R1())


def _vapid_header(endpoint: str, priv_b64: str, pub_b64: str, subject: str) -> dict:
    """Podpisan žeton, s katerim se strežnik predstavi storitvi za obvestila."""
    parts = urllib.parse.urlsplit(endpoint)
    aud = f"{parts.scheme}://{parts.netloc}"

    header = b64e(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    claims = b64e(json.dumps({
        "aud": aud,
        "exp": int(time.time()) + 12 * 3600,
        "sub": subject,
    }, separators=(",", ":")).encode())
    signing_input = f"{header}.{claims}".encode()

    der = _load_private(priv_b64).sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = asym_utils.decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")

    token = f"{header}.{claims}.{b64e(raw)}"
    return {"Authorization": f"vapid t={token}, k={pub_b64}"}


# ── Šifriranje vsebine ───────────────────────────────────────────────────────

def encrypt(payload: bytes, p256dh_b64: str, auth_b64: str) -> bytes:
    """Zašifrira sporočilo za konkretno napravo (aes128gcm)."""
    client_pub_raw = b64d(p256dh_b64)
    auth_secret = b64d(auth_b64)

    client_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), client_pub_raw)
    eph = ec.generate_private_key(ec.SECP256R1())
    eph_pub_raw = eph.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)

    shared = eph.exchange(ec.ECDH(), client_pub)

    # Iz skupne skrivnosti in naročnikove skrivnosti izpeljemo gradivo za ključ
    key_info = b"WebPush: info\x00" + client_pub_raw + eph_pub_raw
    ikm = _hkdf(auth_secret, shared, key_info, 32)

    salt = os.urandom(16)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)

    # 0x02 označuje konec vsebine (zadnji zapis)
    ciphertext = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)

    # Glava zapisa: sol, velikost zapisa, dolžina ključa, ključ
    return (salt + struct.pack("!L", 4096) + bytes([len(eph_pub_raw)])
            + eph_pub_raw + ciphertext)


# ── Pošiljanje ───────────────────────────────────────────────────────────────

class PushError(Exception):
    def __init__(self, status, message=""):
        super().__init__(f"{status}: {message}")
        self.status = status


def send(subscription: dict, data: dict, priv_b64: str, pub_b64: str,
         subject: str = "mailto:info@r-parts.si", ttl: int = 86400):
    """Pošlje obvestilo. Ob napaki 404/410 naročnina ne velja več."""
    endpoint = subscription["endpoint"]
    body = encrypt(json.dumps(data).encode(), subscription["p256dh"], subscription["auth"])

    headers = _vapid_header(endpoint, priv_b64, pub_b64, subject)
    headers.update({
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": str(ttl),
        "Urgency": "high",
    })

    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        raise PushError(e.code, e.read()[:200].decode(errors="replace"))
    except Exception as e:
        raise PushError(0, str(e))
