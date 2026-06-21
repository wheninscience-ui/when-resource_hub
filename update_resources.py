#!/usr/bin/env python3
"""
WHEN Resource Hub - automatic resource updater.

What it does, every time it runs (the GitHub Action runs it on a 48h schedule):
  1. Loads the hand-curated core list from curated.json (always kept).
  2. Pulls new fellowship listings from one or more public RSS feeds (FEEDS below).
  3. Filters feed items to genuine fellowship opportunities, normalises them to the
     hub's resource schema, removes duplicates, and caps how many auto items appear.
  4. Optionally checks that curated links are still alive and flags dead ones.
  5. Writes resources.json, which the website loads automatically.

It never deletes curated entries. Feed items are clearly marked source:"auto"
so a human can review them before promoting them into curated.json.

Run locally:   python update_resources.py
Dependencies:  pip install feedparser requests
"""

import json
import re
import html
import datetime
import sys

try:
    import feedparser
except ImportError:
    feedparser = None
try:
    import requests
except ImportError:
    requests = None

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------

# RSS feeds to scan for new fellowships.
# Get the exact RSS URL for the area you want from https://www.jobs.ac.uk/feeds
# (open a subject-area or job-type page and copy the RSS link), then paste it here.
# You can add EURAXESS, university feeds, or any other RSS source the same way.
FEEDS = [
    # ("Label shown as scope", "https://feed-url", "default category"),
    ("UK", "https://www.jobs.ac.uk/feeds/subject-areas/biological-sciences", "Fellowships and awards"),
    ("UK", "https://www.jobs.ac.uk/feeds/subject-areas/computer-science", "Fellowships and awards"),
]

# Only keep feed items whose title or summary contains one of these words.
KEYWORDS = ["fellow", "fellowship"]

# Words that, if present, drop the item (filters out unrelated admin/support roles).
EXCLUDE = ["cleaner", "porter", "catering", "security officer"]

MAX_AUTO_ITEMS = 30          # cap on auto-fetched items in the published file
CHECK_CURATED_LINKS = True   # HEAD-check curated URLs and flag dead ones
REQUEST_TIMEOUT = 15

# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------

def clean(text, limit=160):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text).replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text

def norm_key(item):
    title = re.sub(r"[^a-z0-9]", "", (item.get("t", "")).lower())
    link = (item.get("u", "")).split("?")[0].rstrip("/").lower()
    return link or title

def month_label(entry):
    for attr in ("published_parsed", "updated_parsed"):
        t = entry.get(attr)
        if t:
            return datetime.date(t.tm_year, t.tm_mon, t.tm_mday).strftime("%d %b")
    return "Open"

# ----------------------------------------------------------------------
# LOAD CURATED
# ----------------------------------------------------------------------

def load_curated():
    try:
        with open("curated.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("WARNING: curated.json not found, starting empty", file=sys.stderr)
        return []

# ----------------------------------------------------------------------
# FETCH FEEDS
# ----------------------------------------------------------------------

def fetch_feeds():
    items = []
    if feedparser is None:
        print("feedparser not installed, skipping feeds", file=sys.stderr)
        return items
    for scope, url, category in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            print(f"feed error {url}: {e}", file=sys.stderr)
            continue
        for e in parsed.entries:
            title = clean(e.get("title", ""), 140)
            summary = clean(e.get("summary", ""), 160)
            blob = (title + " " + summary).lower()
            if not any(k in blob for k in KEYWORDS):
                continue
            if any(x in blob for x in EXCLUDE):
                continue
            items.append({
                "t": title,
                "u": e.get("link", ""),
                "c": category,
                "s": "All stages",
                "scope": scope,
                "cost": "Free",
                "day": "",
                "mon": month_label(e),
                "desc": summary or "New fellowship listing.",
                "tags": ["fellowship", "auto"],
                "source": "auto",
                "status": "review",
            })
    return items

# ----------------------------------------------------------------------
# LINK CHECK
# ----------------------------------------------------------------------

def check_link(url):
    if not requests or not url.startswith("http"):
        return True
    try:
        r = requests.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT,
                          headers={"User-Agent": "WHEN-Hub-LinkCheck/1.0"})
        if r.status_code >= 400:
            r = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True,
                             headers={"User-Agent": "WHEN-Hub-LinkCheck/1.0"})
        return r.status_code < 400
    except Exception:
        return False

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    curated = load_curated()

    if CHECK_CURATED_LINKS:
        for item in curated:
            alive = check_link(item.get("u", ""))
            item["link_ok"] = bool(alive)
            if not alive:
                print(f"DEAD LINK: {item.get('t')} -> {item.get('u')}", file=sys.stderr)

    auto = fetch_feeds()

    seen = {norm_key(i) for i in curated}
    merged = list(curated)
    added = 0
    for item in auto:
        k = norm_key(item)
        if k and k not in seen:
            seen.add(k)
            merged.append(item)
            added += 1
            if added >= MAX_AUTO_ITEMS:
                break

    today = datetime.date.today().isoformat()
    payload = {
        "updated": today,
        "count": len(merged),
        "auto_added": added,
        "resources": merged,
    }
    with open("resources.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"resources.json written: {len(merged)} total, {added} auto-added, updated {today}")

if __name__ == "__main__":
    main()
