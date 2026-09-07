"""Atomic UTF-8 JSON writes shared by all document formats."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def write_json(data: dict, path: str | Path) -> None:
    """Replace a JSON file atomically, preserving its previous contents on failure."""
    destination = Path(path)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
