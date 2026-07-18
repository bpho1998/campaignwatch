"""
Shared persistence + RSS feed generation.

Keeps a JSON set of item IDs we've already alerted on (so re-running the
watchers doesn't re-announce the same filing), and rebuilds feed.xml with
new items prepended each run.
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from feedgen.feed import FeedGenerator

import config


@dataclass
class WatchItem:
    """One alertable event: a donation or a filing."""
    id: str          # stable unique id, used for de-duplication
    title: str
    link: str
    description: str
    published: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _ensure_state_dir():
    os.makedirs(config.STATE_DIR, exist_ok=True)


def load_seen() -> set:
    _ensure_state_dir()
    if not os.path.exists(config.SEEN_STORE_PATH):
        return set()
    with open(config.SEEN_STORE_PATH, "r") as f:
        return set(json.load(f))


def save_seen(seen: set):
    _ensure_state_dir()
    with open(config.SEEN_STORE_PATH, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def load_existing_feed_items() -> list:
    """Re-read feed.xml (if present) so we can prepend new items to it
    rather than clobbering history each run."""
    if not os.path.exists(config.FEED_PATH):
        return []
    try:
        fg = FeedGenerator()
        fg.load_extension("dc", atom=True)
    except Exception:
        pass
    # feedgen doesn't support re-parsing its own output out of the box,
    # so we keep a parallel JSON log of raw items for rebuilding.
    log_path = config.FEED_PATH.replace(".xml", "_items.json")
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r") as f:
        raw = json.load(f)
    items = []
    for r in raw:
        items.append(WatchItem(
            id=r["id"], title=r["title"], link=r["link"],
            description=r["description"],
            published=datetime.fromisoformat(r["published"]),
        ))
    return items


def _save_items_log(items: list):
    log_path = config.FEED_PATH.replace(".xml", "_items.json")
    with open(log_path, "w") as f:
        json.dump([{
            "id": i.id, "title": i.title, "link": i.link,
            "description": i.description, "published": i.published.isoformat(),
        } for i in items], f, indent=2)


def write_feed(new_items: list, max_items: int = 300):
    """Prepend new_items to the existing feed and rewrite feed.xml."""
    _ensure_state_dir()
    existing = load_existing_feed_items()
    existing_ids = {i.id for i in existing}
    combined = [i for i in new_items if i.id not in existing_ids] + existing
    # newest first, capped
    combined.sort(key=lambda i: i.published, reverse=True)
    combined = combined[:max_items]

    fg = FeedGenerator()
    fg.title(config.FEED_TITLE)
    fg.link(href=config.FEED_LINK, rel="alternate")
    fg.description(config.FEED_DESCRIPTION)
    fg.language("en")

    for item in combined:
        fe = fg.add_entry()
        fe.id(item.id)
        fe.title(item.title)
        fe.link(href=item.link)
        fe.description(item.description)
        fe.pubDate(item.published)

    fg.rss_file(config.FEED_PATH, pretty=True)
    _save_items_log(combined)
    return len(new_items)
