from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from uuid import uuid4

from services.storage import DATA_DIR, read_json, write_json

BOOKMARKS_PATH = DATA_DIR / "bookmarks.json"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def normalize_bookmark(raw: dict[str, Any]) -> dict[str, Any]:
    now = _now_iso()
    return {
        "id": raw.get("id") or str(uuid4()),
        "title": str(raw.get("title", "Unbenannt")).strip() or "Unbenannt",
        "url": str(raw.get("url", "")).strip(),
        "category": str(raw.get("category", "Allgemein")).strip() or "Allgemein",
        "tags": _normalize_tags(raw.get("tags")),
        "favorite": bool(raw.get("favorite", False)),
        "source": str(raw.get("source", "manual")).strip() or "manual",
        "created_at": raw.get("created_at") or now,
        "updated_at": now,
    }


def load_bookmarks() -> list[dict[str, Any]]:
    data = read_json(BOOKMARKS_PATH, [])
    if not isinstance(data, list):
        return []
    return [normalize_bookmark(item) for item in data if isinstance(item, dict)]


def save_bookmarks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    write_json(BOOKMARKS_PATH, items)
    return items


def list_bookmarks(
    query: str = "",
    category: str | None = None,
    favorite: bool | None = None,
    sort_by: str = "title",
    sort_order: str = "asc",
) -> list[dict[str, Any]]:
    items = load_bookmarks()
    q = query.strip().lower()

    if q:
        items = [
            item
            for item in items
            if q in item["title"].lower()
            or q in item["url"].lower()
            or q in item["category"].lower()
            or any(q in tag.lower() for tag in item.get("tags", []))
        ]

    if category:
        items = [item for item in items if item.get("category", "").lower() == category.lower()]

    if favorite is not None:
        items = [item for item in items if item.get("favorite") is favorite]

    reverse = sort_order.lower() == "desc"
    allowed_sort_keys = {"title", "category", "created_at", "updated_at", "url"}
    key = sort_by if sort_by in allowed_sort_keys else "title"
    items.sort(key=lambda x: str(x.get(key, "")).lower(), reverse=reverse)
    return items


def create_bookmark(raw: dict[str, Any]) -> dict[str, Any]:
    items = load_bookmarks()
    bookmark = normalize_bookmark(raw)
    items.append(bookmark)
    save_bookmarks(items)
    return bookmark


def update_bookmark(bookmark_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    items = load_bookmarks()

    for idx, item in enumerate(items):
        if item.get("id") == bookmark_id:
            merged = {**item, **patch, "id": bookmark_id}
            items[idx] = normalize_bookmark(merged)
            save_bookmarks(items)
            return items[idx]

    return None


def delete_bookmark(bookmark_id: str) -> bool:
    items = load_bookmarks()
    filtered = [item for item in items if item.get("id") != bookmark_id]
    if len(filtered) == len(items):
        return False
    save_bookmarks(filtered)
    return True


def list_categories() -> list[str]:
    categories = sorted({item.get("category", "Allgemein") for item in load_bookmarks()})
    return categories


@dataclass
class BookmarkImportResult:
    imported: int
    skipped: int


class NetscapeBookmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_category = "Importiert"
        self.in_h3 = False
        self.in_a = False
        self.current_link: dict[str, str] = {}
        self.items: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag.lower() == "h3":
            self.in_h3 = True

        if tag.lower() == "a":
            self.in_a = True
            self.current_link = {
                "url": attrs_dict.get("href", "").strip(),
                "title": "",
                "category": self.current_category,
                "source": "browser-export",
            }

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h3":
            self.in_h3 = False
        if tag.lower() == "a":
            self.in_a = False
            if self.current_link.get("url"):
                self.items.append(normalize_bookmark(self.current_link))
            self.current_link = {}

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return

        if self.in_h3:
            self.current_category = value

        if self.in_a and self.current_link is not None:
            self.current_link["title"] = value


def import_bookmarks_from_json(payload: list[dict[str, Any]]) -> BookmarkImportResult:
    existing = load_bookmarks()
    existing_urls = {item.get("url", "") for item in existing}

    imported = 0
    skipped = 0

    for raw in payload:
        if not isinstance(raw, dict):
            skipped += 1
            continue

        candidate = normalize_bookmark(raw)
        if candidate.get("url") in existing_urls:
            skipped += 1
            continue

        existing.append(candidate)
        existing_urls.add(candidate.get("url", ""))
        imported += 1

    save_bookmarks(existing)
    return BookmarkImportResult(imported=imported, skipped=skipped)


def import_bookmarks_from_netscape_html(html: str) -> BookmarkImportResult:
    parser = NetscapeBookmarkParser()
    parser.feed(html)
    return import_bookmarks_from_json(parser.items)
