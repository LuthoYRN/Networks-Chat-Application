# task1.py
import base64
import os
import time
import struct
import traceback
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

CONSTRUCTION = b"Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s"
IDENTIFIER = b"WireGuard v1 zx2c4 Jason@zx2c4.com"
LABEL_MAC1 = b"mac1----"
TAI64N_OFFSET = 4611686018427387914

CLIENT_STATIC_PRIVATE_B64 = "43Fd+IQXDBaf/ljJroA+Inn3mbEyM1sMjcpkG+Gg3jA="
SERVER_STATIC_PUBLIC_B64 = "ZixewENi85M3vxEUIu0TC5/nrzuUsHAT4ZTdhc8BC0M="

def load_base64_key(b64_string):
    return base64.b64decode(b64_string)

def blake2s(data: bytes) -> bytes:
    digest = hashes.Hash(hashes.BLAKE2s(32))
    digest.update(data)
    return digest.finalize()

def hmac_hash(key: bytes, data: bytes) -> bytes:
    h = hmac.HMAC(key, hashes.BLAKE2s(32))
    h.update(data)
    return h.finalize()

def aead_encrypt(key: bytes, counter: int, plaintext: bytes, aad: bytes) -> bytes:
    nonce = b"\x00" * 4 + struct.pack("<Q", counter)
    cipher = ChaCha20Poly1305(key)
    return cipher.encrypt(nonce, plaintext, aad)



def aead_decrypt(key: bytes, counter: int, ciphertext_with_tag: bytes, aad: bytes) -> bytes:
    nonce = b"\x00" * 4 + struct.pack("<Q", counter)
    cipher = ChaCha20Poly1305(key)
    try:
        return cipher.decrypt(nonce, ciphertext_with_tag, aad)
    except Exception as e:
        print("[DECRYPT FAIL] Exception during decrypt:", repr(e))
        traceback.print_exc()
        raise

def tai64n_timestamp():
    tai64n = int(time.time()) + TAI64N_OFFSET
    nano = int(time.time_ns() % 1_000_000_000)
    return struct.pack(">Q", tai64n) + struct.pack(">I", nano // 1000)

def derive_key_pair():
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

# Generate static and ephemeral keys
client_static_private_bytes = load_base64_key(CLIENT_STATIC_PRIVATE_B64)
server_static_public_bytes = load_base64_key(SERVER_STATIC_PUBLIC_B64)

client_static_private = x25519.X25519PrivateKey.from_private_bytes(client_static_private_bytes)
client_static_public = client_static_private.public_key()
client_static_public_bytes = client_static_public.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)

server_static_public = x25519.X25519PublicKey.from_public_bytes(server_static_public_bytes)

ephemeral_private, ephemeral_public = derive_key_pair()
ephemeral_public_bytes = ephemeral_public.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)

# Export values needed by task2
__all__ = [
    "CONSTRUCTION", "IDENTIFIER", "LABEL_MAC1",
    "client_static_private", "client_static_public_bytes",
    "server_static_public", "ephemeral_private", "ephemeral_public_bytes",
    "blake2s", "hmac_hash", "aead_encrypt", "tai64n_timestamp", "aead_decrypt"
]
