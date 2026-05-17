from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import sys

from ai_news_alerts.models import BriefItem


class SeenStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._seen: dict[str, str] = {}
        if self.path.exists():
            self._seen = self._load()

    def is_seen(self, item: BriefItem) -> bool:
        return self.is_seen_fingerprint(item.fingerprint)

    def is_seen_fingerprint(self, fingerprint: str) -> bool:
        return fingerprint in self._seen

    def mark_seen(self, item: BriefItem) -> None:
        self._seen[item.fingerprint] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        _write_seen(self.path, self._seen)

    def _load(self) -> dict[str, str]:
        return _load_seen(self.path)


def merge_seen_files(destination: Path, incoming: Path) -> None:
    merged = _load_seen(destination)
    for fingerprint, timestamp in _load_seen(incoming).items():
        current = merged.get(fingerprint)
        if current is None or timestamp > current:
            merged[fingerprint] = timestamp
    _write_seen(destination, merged)


def _load_seen(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    seen = payload.get("seen", {})
    if not isinstance(seen, dict):
        return {}
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in seen.items()):
        return {}
    return dict(seen)


def _write_seen(path: Path, seen: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump({"seen": seen}, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3 or args[0] != "merge":
        print("Usage: python -m ai_news_alerts.seen merge <destination> <incoming>", file=sys.stderr)
        return 2
    merge_seen_files(Path(args[1]), Path(args[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
