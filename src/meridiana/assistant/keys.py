"""The keys of the cloud providers (study 14, 6.7) and of the map sources the designer adds (R36, `service` =
"meridiana-maps", one name for each source): in the system's keyring through `keyring` (Windows Credential Locker,
the Secret Service on Linux), never in a file, a log or the settings. `keyring` is imported only here and only when
a key is wanted: without it the program starts and the cloud is simply not offered. No Qt."""

from __future__ import annotations

from .. import SLUG

SERVICE = f"{SLUG}-assistant"


class KeyringMissing(Exception):
    """No keyring on this system (the library absent, or no backend that keeps secrets)."""


def _keyring():
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError as error:
        raise KeyringMissing("keyring") from error
    return keyring, KeyringError


def get(provider: str, service: str = SERVICE) -> str:
    """The key of `provider`, "" when there is none; KeyringMissing when it cannot be asked."""
    keyring, error = _keyring()
    try:
        return keyring.get_password(service, provider) or ""
    except error as e:
        raise KeyringMissing(str(e)) from e


def put(provider: str, key: str, service: str = SERVICE) -> None:
    keyring, error = _keyring()
    try:
        keyring.set_password(service, provider, key.strip())
    except error as e:
        raise KeyringMissing(str(e)) from e


def forget(provider: str, service: str = SERVICE) -> None:
    """The key of `provider` out of the keyring; none there is not a failure, any other one is (KeyringMissing)."""
    keyring, error = _keyring()
    from keyring.errors import PasswordDeleteError
    try:
        keyring.delete_password(service, provider)
    except PasswordDeleteError:
        return                  # there was none: nothing to forget
    except error as e:
        raise KeyringMissing(str(e)) from e


def masked(key: str) -> str:
    """A key as it may be shown: its first characters and its last four («sk-ant-…a1b2»)."""
    key = key.strip()
    if len(key) <= 12:
        return "…" if key else ""
    return f"{key[:7]}…{key[-4:]}"
