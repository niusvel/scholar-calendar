"""Small clock helpers shared by configuration, planning and the desktop UI."""

from datetime import time

DEFAULT_CLASS_START = time(8, 30)


def minutes_since_midnight(value: time) -> int:
    return value.hour * 60 + value.minute


def parse_optional_time(value: str) -> time | None:
    value = value.strip()
    return time.fromisoformat(value) if value else None
