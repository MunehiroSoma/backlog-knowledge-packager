import json

from backlog_packager.sync import filter_updated_items, load_cached_items, should_fetch


def test_missing_cache_fetches_everything(tmp_path) -> None:
    cache = load_cached_items(tmp_path / "source-map.json")

    assert cache == {}
    assert should_fetch("document", "1", "2026-07-01T00:00:00+09:00", cache)


def test_invalid_cache_is_ignored(tmp_path) -> None:
    source_map = tmp_path / "source-map.json"
    source_map.write_text("{not json", encoding="utf-8")

    assert load_cached_items(source_map) == {}


def test_cache_ignores_unexpected_shape_and_non_object_items(tmp_path) -> None:
    source_map = tmp_path / "source-map.json"
    source_map.write_text(json.dumps({"items": ["bad", 1, None]}), encoding="utf-8")

    assert load_cached_items(source_map) == {}


def test_cache_skips_unchanged_items(tmp_path) -> None:
    source_map = tmp_path / "source-map.json"
    source_map.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "sourceType": "document",
                        "sourceId": "1",
                        "updated": "2026-07-01T00:00:00+09:00",
                        "contentPath": "files/documents/rule.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cache = load_cached_items(source_map)

    assert not should_fetch("document", "1", "2026-07-01T00:00:00+09:00", cache)
    assert should_fetch("document", "1", "2026-07-02T00:00:00+09:00", cache)
    assert cache[("document", "1")].content_path == "files/documents/rule.md"


def test_cache_drops_unsafe_content_paths(tmp_path) -> None:
    source_map = tmp_path / "source-map.json"
    source_map.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "sourceType": "document",
                        "sourceId": "1",
                        "updated": "2026-07-01T00:00:00+09:00",
                        "contentPath": "../outside.md",
                    },
                    {
                        "sourceType": "wiki",
                        "sourceId": "2",
                        "updated": "2026-07-01T00:00:00+09:00",
                        "contentPath": str(tmp_path / "outside.md"),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    cache = load_cached_items(source_map)

    assert cache[("document", "1")].content_path is None
    assert cache[("wiki", "2")].content_path is None


def test_filter_updated_items_keeps_new_or_changed_items() -> None:
    cache = {
        ("document", "1"): type("Cached", (), {"updated": "2026-07-01T00:00:00+09:00"})(),
        ("document", "2"): type("Cached", (), {"updated": "2026-07-01T00:00:00+09:00"})(),
    }

    filtered = filter_updated_items(
        "document",
        [
            {"id": "1", "updated": "2026-07-01T00:00:00+09:00"},
            {"id": "2", "updated": "2026-07-02T00:00:00+09:00"},
            {"id": "3", "updated": "2026-07-01T00:00:00+09:00"},
        ],
        cache,
    )

    assert [item["id"] for item in filtered] == ["2", "3"]
