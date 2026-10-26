import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Iterator


DATA_DIR = Path(__file__).resolve().parent
_LOCK = RLock()


@contextmanager
def transaction() -> Iterator[None]:
    with _LOCK:
        yield


def read_json(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    with _LOCK:
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except OSError:
            raise
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON data in {filename}") from exc
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise RuntimeError(f"Expected a JSON list of objects in {filename}")
        return data


def write_json(filename: str, records: list[dict[str, Any]]) -> None:
    path = DATA_DIR / filename
    with _LOCK:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=DATA_DIR
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
                json.dump(records, temporary, indent=2, ensure_ascii=False)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, path)
        except OSError:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
