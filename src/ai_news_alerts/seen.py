from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=self.path.parent,
                encoding="utf-8",
                prefix=f".{self.path.name}.",
                suffix=".tmp",
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump({"seen": self._seen}, temp_file, indent=2, sort_keys=True)
                temp_file.write("\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())
            temp_path.replace(self.path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def _load(self) -> dict[str, str]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
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
