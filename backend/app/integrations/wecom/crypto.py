from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class WeComCrypto:
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str) -> None:
        self._token = token
        self._key = base64.b64decode(encoding_aes_key + "=")
        self._corp_id = corp_id

    def _sign(self, timestamp: str, nonce: str, encrypt: str) -> str:
        items = sorted([self._token, timestamp, nonce, encrypt])
        return hashlib.sha1("".join(items).encode()).hexdigest()

    def verify_signature(
        self, msg_signature: str, timestamp: str, nonce: str, echostr: str
    ) -> bool:
        expected = self._sign(timestamp, nonce, echostr)
        return _hmac.compare_digest(expected.encode(), msg_signature.encode())

    def decrypt(self, encrypted: str) -> str:
        ciphertext = base64.b64decode(encrypted)
        cipher = Cipher(algorithms.AES(self._key), modes.CBC(self._key[:16]))
        decryptor = cipher.decryptor()
        raw = decryptor.update(ciphertext) + decryptor.finalize()
        # Remove PKCS7 padding
        pad = raw[-1]
        raw = raw[:-pad]
        # Skip 16-byte random header; read 4-byte length
        raw = raw[16:]
        msg_len = struct.unpack(">I", raw[:4])[0]
        return raw[4 : 4 + msg_len].decode("utf-8")

    def encrypt(self, message: str) -> str:
        msg_bytes = message.encode("utf-8")
        random_bytes = b"\x00" * 16
        length_bytes = struct.pack(">I", len(msg_bytes))
        raw = random_bytes + length_bytes + msg_bytes + self._corp_id.encode()
        # PKCS7 pad to multiple of 32
        pad = 32 - len(raw) % 32
        raw += bytes([pad] * pad)
        cipher = Cipher(algorithms.AES(self._key), modes.CBC(self._key[:16]))
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(raw) + encryptor.finalize()
        return base64.b64encode(encrypted).decode()

    def gen_signature(self, timestamp: str, nonce: str, encrypted: str) -> str:
        return self._sign(timestamp, nonce, encrypted)
