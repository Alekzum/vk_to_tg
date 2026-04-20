from cryptography.fernet import Fernet
import os


def get_token() -> bytes:
    return os.environ["SECRET_TOKEN"].encode("utf-8")


# Source - https://stackoverflow.com/a/55147077
# Posted by Martijn Pieters, modified by community. See post 'Timeline' for change history
# Retrieved 2026-04-20, License - CC BY-SA 4.0
def get_fernet():
    return Fernet(get_token())


def encrypt(message: bytes) -> bytes:
    return get_fernet().encrypt(message)


def decrypt(token: bytes) -> bytes:
    return get_fernet().decrypt(token)


def get_bytes(string: str | bytes) -> bytes:
    if isinstance(string, bytes):
        return string
    elif isinstance(string, str):
        return string.encode("utf-8")
    raise TypeError(f"Unknown type {type(string)}!")


def decrypt_string(string: str | bytes | None = None) -> str:
    if string is None:
        return ""
    data = get_bytes(string)
    return decrypt(data).decode("utf-8")


def encrypt_string(string: str) -> str:
    if string is None:
        return ""
    data = get_bytes(string)
    return encrypt(data).decode("utf-8")
