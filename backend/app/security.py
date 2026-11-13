import hashlib
import hmac
import secrets


def new_salt() -> str:
    return secrets.token_hex(16).upper()


def hash_password(salt: str, password: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest().upper()


def verify_password(salt: str, password: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_password(salt, password), stored_hash.upper())


def new_token() -> str:
    return secrets.token_hex(32)
