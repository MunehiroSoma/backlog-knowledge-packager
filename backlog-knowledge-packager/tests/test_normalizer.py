from backlog_packager.collector import CollectionResult
from backlog_packager.normalizer import normalize_collection


def test_normalize_collection_creates_source_backed_items(tmp_path) -> None:
    collection = CollectionResult(
        documents=[
            {
                "id": "1",
                "title": "setup guide",
                "plain": "install docker",
                "created": "2026-07-01T00:00:00Z",
                "updated": "2026-07-02T00:00:00Z",
                "createdUser": {"name": "Alice"},
                "updatedUser": {"userId": "bob"},
                "tags": [{"name": "env"}],
            }
        ],
        wikis=[
            {
                "id": 2,
                "name": "team rule",
                "content": "review rule",
                "updated": "2026-07-03T00:00:00Z",
            }
        ],
        shared_files=[
            {
                "id": 3,
                "type": "file",
                "dir": "/templates/",
                "name": "issue-template.md",
                "updated": "2026-07-04T00:00:00Z",
                "contentPath": "files/shared/templates/issue-template.md",
            }
        ],
        attachments=[
            {
                "id": 4,
                "name": "diagram.png",
                "parentType": "document",
                "parentId": "1",
                "parentUrl": "https://space.backlog.com/document/1",
                "created": "2026-07-05T00:00:00Z",
                "contentPath": "files/attachments/documents/1/diagram.png",
            }
        ],
    )

    items = normalize_collection(collection, "DEMO", "https://space.backlog.com", tmp_path)

    assert [item.source_type for item in items] == ["document", "wiki", "sharedFile", "attachment"]
    assert items[0].url == "https://space.backlog.com/document/1"
    assert items[0].content_path == "files/documents/setup-guide.md"
    assert (tmp_path / "files" / "documents" / "setup-guide.md").read_text(encoding="utf-8") == "install docker"
    assert items[1].url == "https://space.backlog.com/alias/wiki/2"
    assert items[2].url == "https://space.backlog.com/file/DEMO/templates/issue-template.md"
    assert items[3].url == "https://space.backlog.com/document/1"
    assert items[3].content_path == "files/attachments/documents/1/diagram.png"


def test_normalize_skips_items_without_required_source_context(tmp_path) -> None:
    collection = CollectionResult(documents=[{"id": "1", "title": "missing updated", "plain": "body"}])

    assert normalize_collection(collection, "DEMO", "https://space.backlog.com", tmp_path) == []


def test_normalize_reuses_cached_content_path_when_raw_has_no_content(tmp_path) -> None:
    cached = tmp_path / "files" / "wikis" / "team-rule.md"
    cached.parent.mkdir(parents=True)
    cached.write_text("cached wiki body", encoding="utf-8")
    collection = CollectionResult(
        wikis=[
            {
                "id": "1",
                "name": "team rule",
                "updated": "2026-07-02T00:00:00Z",
                "contentPath": "files/wikis/team-rule.md",
            }
        ]
    )

    items = normalize_collection(collection, "DEMO", "https://space.backlog.com", tmp_path)

    assert items[0].content == "cached wiki body"
    assert items[0].content_path == "files/wikis/team-rule.md"


def test_normalize_does_not_read_unsafe_cached_content_path(tmp_path) -> None:
    outside = tmp_path.parent / "outside-cache.md"
    outside.write_text("outside body", encoding="utf-8")
    collection = CollectionResult(
        documents=[
            {
                "id": "1",
                "title": "team rule",
                "updated": "2026-07-02T00:00:00Z",
                "contentPath": "../outside-cache.md",
            }
        ]
    )

    items = normalize_collection(collection, "DEMO", "https://space.backlog.com", tmp_path)

    assert items[0].content == ""
    assert items[0].content_path is None
