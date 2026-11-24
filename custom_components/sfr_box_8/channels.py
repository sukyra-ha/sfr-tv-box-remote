"""Validate channel numbers and configurable favorites."""

import re

_CHANNEL_NUMBER = re.compile(r"[0-9]{1,4}")


def channel_number(value: str) -> str:
    """Accept one to four ASCII digits, preserving leading zeroes."""
    value = value.strip()
    if not _CHANNEL_NUMBER.fullmatch(value):
        raise ValueError("Le numéro de chaîne doit contenir 1 à 4 chiffres")
    return value


def channels_from_text(text: str) -> dict[str, str]:
    """Parse a number or a 'number = name' per line."""
    channels = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        number, _, name = line.partition("=")
        number = channel_number(number)
        source = f"{number} · {name.strip()}" if name.strip() else number
        if source in channels:
            raise ValueError(f"Chaîne déjà définie : {source}")
        channels[source] = number
    return channels
