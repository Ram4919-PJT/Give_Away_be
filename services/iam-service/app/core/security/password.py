import hashlib

import bcrypt

# Bcrypt accepts at most 72 bytes; pre-hash so longer passwords still work.
def _password_digest(plain_password: str) -> bytes:
    return hashlib.sha256(plain_password.encode("utf-8")).digest()


def hash_password(plain_password: str) -> str:
    digest = _password_digest(plain_password)
    return bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    digest = _password_digest(plain_password)
    return bcrypt.checkpw(digest, password_hash.encode("utf-8"))
