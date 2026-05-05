import json

from ai_news_alerts.models import BriefItem
from ai_news_alerts.seen import SeenStore


def _item(fingerprint: str = "abc") -> BriefItem:
    return BriefItem(
        title="Title",
        why_it_matters="Why",
        quick_read="Read",
        signal="Signal",
        phrase="phrase",
        source_url="https://example.com",
        discussion_url=None,
        fingerprint=fingerprint,
    )


def test_seen_store_loads_invalid_json_as_empty(tmp_path) -> None:
    path = tmp_path / "seen.json"
    path.write_text("not json", encoding="utf-8")

    store = SeenStore(path)

    assert store.is_seen(_item()) is False


def test_seen_store_marks_and_saves_schema(tmp_path) -> None:
    path = tmp_path / "seen.json"
    store = SeenStore(path)

    store.mark_seen(_item("item-1"))
    store.save()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"seen"}
    assert "item-1" in payload["seen"]


def test_constructing_store_does_not_create_file_for_dry_run(tmp_path) -> None:
    path = tmp_path / "seen.json"

    SeenStore(path)

    assert not path.exists()
