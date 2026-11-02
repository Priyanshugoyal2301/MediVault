"""RFC 6238 TOTP with replay counters and high-entropy, single-use recovery codes."""
import base64
import hashlib
import hmac
import secrets
import struct
import time


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def code_at(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff
    return f"{value % 1000000:06d}"


def verify_code(secret: str, code: str, last_counter=-1, timestamp=None):
    if len(code) != 6 or not code.isdigit():
        return None
    current = int((time.time() if timestamp is None else timestamp) // 30)
    for counter in (current, current - 1, current + 1):
        if counter > last_counter and hmac.compare_digest(code_at(secret, counter), code):
            return counter
    return None


def recovery_codes():
    codes = [secrets.token_urlsafe(18) for _ in range(8)]
    return codes, [hashlib.sha256(code.encode()).hexdigest() for code in codes]


def consume_recovery(hashes, code):
    digest = hashlib.sha256(code.encode()).hexdigest()
    if not any(hmac.compare_digest(digest, item) for item in hashes):
        return None
    return [item for item in hashes if not hmac.compare_digest(digest, item)]
