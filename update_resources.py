#!/usr/bin/env python3
"""
WHEN Resource Hub - weekly updater.

The GitHub Action runs this every Monday. Each run:
  1. Loads the hand-checked list in curated.json (never deletes anything).
  2. Works out the deadline status of every fellowship from its "deadline" field:
       open        the deadline is in the future
       soon        the deadline is within CLOSING_SOON_DAYS days
       closed      the deadline has passed, so the site shows the next expected round
       window      no exact date yet, so the site shows the usual period ("window")
  3. Watches the official page of every fellowship. If the part of the page that
     talks about dates and deadlines has changed since last week, the item is
     listed in CHANGES.md. The Action turns that file into a GitHub Issue, so you
     get an email telling you exactly which calls to check.
  4. Checks that links still work.
  5. Optionally adds items from RSS feeds (FEEDS below), marked "under review".
  6. Writes resources.json, which the website loads.
  7. Writes deadlines.ics, a calendar of all upcoming deadlines that anyone can
     subscribe to in Outlook or Google Calendar.
  8. Writes DIGEST.md, a ready-to-send email of the deadlines in the next 60 days.

Run locally:   python update_resources.py
Dependencies:  pip install feedparser requests
"""

import datetime
import hashlib
import html
import json
import re
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

CLOSING_SOON_DAYS = 21
CHECK_LINKS = True
WATCH_PAGES = True
REQUEST_TIMEOUT = 20
WATCH_CATEGORIES = {"Fellowships and awards", "Funding opportunities"}

# Optional RSS feeds. Paste a real RSS link (it starts with "<?xml" when opened).
FEEDS = [
    # ("UK", "PASTE_REAL_RSS_LINK_HERE", "Fellowships and awards"),
]
KEYWORDS = ["fellow", "fellowship"]
EXCLUDE = ["cleaner", "porter", "catering", "security officer"]
MAX_AUTO_ITEMS = 20

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36 WHEN-Resource-Hub",
    "Accept-Language": "en-GB,en;q=0.9",
}

MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
DATE_LINE = re.compile(
    r"(deadline|closing|closes|close on|opens|open for|open until|apply by|submission|round|call)"
    r"|(\b\d{1,2}\s+(" + MONTHS + r")\b)|(\b(" + MONTHS + r")\s+20\d\d\b)",
    re.I,
)

TODAY = datetime.date.today()

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
    title = re.sub(r"[^a-z0-9]", "", item.get("t", "").lower())
    link = item.get("u", "").split("?")[0].rstrip("/").lower()
    return link or title


def get(url):
    if not requests or not url.startswith("http"):
        return None
    try:
        return requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    except Exception as e:
        print(f"request failed {url}: {e}", file=sys.stderr)
        return None


def page_fingerprint(text):
    """Keep only the sentences that mention dates, deadlines or rounds, then hash them.
    This ignores cookie banners, menus and other parts of the page that change often."""
    text = re.sub(r"(?is)<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    keep = sorted({l for l in lines if 12 <= len(l) <= 400 and DATE_LINE.search(l)})
    return hashlib.sha256("\n".join(keep).encode("utf-8")).hexdigest(), keep[:8]

# ----------------------------------------------------------------------
# DEADLINES
# ----------------------------------------------------------------------

def apply_deadline(item):
    """Fill the fields the website shows: day, mon and dl (deadline status)."""
    window = item.get("window") or item.get("mon") or "Rolling"
    dl = item.get("deadline") or ""
    try:
        d = datetime.date.fromisoformat(dl) if dl else None
    except ValueError:
        d = None
    if d and d >= TODAY:
        left = (d - TODAY).days
        item["day"] = d.strftime("%d")
        item["mon"] = d.strftime("%b %Y")
        item["dl"] = "soon" if left <= CLOSING_SOON_DAYS else "open"
        item["days_left"] = left
    elif d:
        item["day"] = ""
        item["mon"] = "Next: " + window
        item["dl"] = "closed"
    else:
        item["day"] = ""
        item["mon"] = window
        item["dl"] = "window"
    return item

# ----------------------------------------------------------------------
# CALENDAR AND EMAIL DIGEST
# ----------------------------------------------------------------------

SITE = "https://wheninscience-ui.github.io/when-resource_hub/"


def ics_escape(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", " ")


def fold(line):
    out = []
    while len(line.encode("utf-8")) > 74:
        cut = 74
        while len(line[:cut].encode("utf-8")) > 74:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)


def write_calendar(items):
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//WHEN//Resource Hub//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:WHEN fellowship deadlines", "X-PUBLISHED-TTL:P1W"]
    for i in items:
        if i.get("dl") not in ("open", "soon"):
            continue
        d = datetime.date.fromisoformat(i["deadline"])
        uid = hashlib.sha1((i["t"] + i["deadline"]).encode("utf-8")).hexdigest()[:16]
        lines += ["BEGIN:VEVENT", f"UID:{uid}@when-resource-hub", f"DTSTAMP:{stamp}",
                  f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + datetime.timedelta(days=1):%Y%m%d}",
                  fold("SUMMARY:Deadline: " + ics_escape(i["t"])),
                  fold("DESCRIPTION:" + ics_escape((i.get("desc") or "") + " " + (i.get("note") or "") + " Check the official page: " + i.get("u", ""))),
                  fold("URL:" + i.get("u", "")),
                  "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-P14D", fold("DESCRIPTION:Two weeks left: " + ics_escape(i["t"])), "END:VALARM",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    open("deadlines.ics", "w", encoding="utf-8", newline="").write("\r\n".join(lines) + "\r\n")


# Monthly selection for the mailing list -------------------------------
# Writes DIGEST.md (plain text, for the GitHub Issue) and DIGEST.html
# (an email ready to open in a browser, select all, copy and paste into Outlook).

PICK_GROUPS = [
    ("Funding and fellowships", {"Fellowships and awards", "Funding opportunities"}),
    ("Help with costs", {"Help with costs"}),
    ("Part-time and family", {"Part-time and flexible work", "Parental leave and flexible working"}),
    ("Inclusion", {"Inclusion and access", "EDI resources", "Mentoring schemes", "Leadership programmes"}),
    ("Housing and living", {"Housing and living"}),
]

def monthly_picks(items):
    """One resource per group, rotating every month, so each issue shows something different."""
    month_index = TODAY.year * 12 + TODAY.month
    picks = []
    for label, cats in PICK_GROUPS:
        pool = sorted([i for i in items if i.get("c") in cats and i.get("status") != "review"
                       and i.get("dl") not in ("open", "soon")], key=lambda i: i["t"])
        if pool:
            picks.append((label, pool[month_index % len(pool)]))
    return picks

def upcoming_events(limit=3):
    try:
        ev = json.load(open("events.json", encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    ev = [e for e in ev if e.get("date", "") >= TODAY.isoformat()]
    ev.sort(key=lambda e: (e["date"], e.get("start", "")))
    return ev[:limit]

def new_this_month(items):
    since = (TODAY - datetime.timedelta(days=31)).isoformat()
    return [i for i in items if i.get("added", "") >= since and i.get("status") != "review"]

def write_digest(items):
    soon = [i for i in items if i.get("dl") in ("open", "soon") and i.get("days_left", 999) <= 75]
    soon.sort(key=lambda i: i["deadline"])
    picks = monthly_picks(items)
    events = upcoming_events()
    fresh = new_this_month(items)
    month = f"{TODAY:%B %Y}"
    subject = f"WHEN Resource Hub, {month} selection"
    when = lambda i: datetime.date.fromisoformat(i["deadline"]).strftime("%-d %B %Y")
    hub = SITE

    # plain text
    out = [f"Subject: {subject}", "", "Dear all,", "",
           f"Here is the {month} selection from the WHEN Resource Hub: deadlines coming up, "
           "a few resources worth knowing, and our next events.", ""]
    out += ["DEADLINES COMING UP", ""]
    out += [f"- {when(i)}: {i['t']}. {i.get('u', '')}" for i in soon] or \
           ["There are no confirmed deadlines in the coming weeks."]
    out += ["", "THIS MONTH'S SELECTION", ""]
    for label, i in picks:
        extra = f" {i['amount']}." if i.get("amount") else ""
        out.append(f"- {label}: {i['t']}. {i.get('desc', '')}{extra} {i.get('u', '')}")
    if fresh and len(fresh) <= 10:
        out += ["", "NEW ON THE HUB", ""] + [f"- {i['t']}. {i.get('u', '')}" for i in fresh]
    elif fresh:
        out += ["", "NEW ON THE HUB", "",
                f"{len(fresh)} new resources this month, including help with childcare and caring costs, "
                "part-time work, housing advice and support for international and minority ethnic researchers."]
    if events:
        out += ["", "WHEN EVENTS", ""]
        for e in events:
            d = datetime.date.fromisoformat(e["date"]).strftime("%a %-d %B")
            out.append(f"- {d}, {e.get('start', '')}: {e['title']}, {e.get('place', '')}. {e.get('link', '')}")
    out += ["", f"All resources: {hub}", f"Every deadline in your calendar: {hub}deadlines.ics",
            f"Did the hub help you? Tell us in one click: {hub}#feedback", "",
            "Best wishes,", "The WHEN team"]
    open("DIGEST.md", "w", encoding="utf-8").write("\n".join(out) + "\n")

    # HTML email (inline styles only, so it survives copy and paste into Outlook)
    E = html.escape
    ink, violet, muted, line = "#2C1A47", "#46296E", "#6B5E80", "#D2C4E6"
    head = lambda txt: (f'<tr><td style="padding:28px 32px 8px;font-family:Courier New,monospace;font-size:12px;'
                        f'letter-spacing:2px;text-transform:uppercase;color:{muted}">{E(txt)}</td></tr>')
    def row(title, url, meta, body=""):
        return (f'<tr><td style="padding:10px 32px;border-bottom:1px solid {line}">'
                f'<a href="{E(url)}" style="font-family:Courier New,monospace;font-weight:bold;font-size:17px;color:{ink};text-decoration:none">{E(title)} &#8599;</a>'
                f'<div style="font-family:Arial,sans-serif;font-size:14px;color:{violet};font-weight:bold;margin-top:3px">{E(meta)}</div>'
                + (f'<div style="font-family:Arial,sans-serif;font-size:14px;color:{muted};margin-top:3px;line-height:1.45">{E(body)}</div>' if body else "")
                + '</td></tr>')
    h = [f'<!doctype html><html><head><meta charset="utf-8"><title>{E(subject)}</title></head>',
         f'<body style="margin:0;background:#F4F0F9"><p style="font-family:Arial,sans-serif;font-size:13px;color:{muted};text-align:center;margin:16px">'
         f'Subject: <b>{E(subject)}</b><br>Select all, copy and paste into a new email.</p>',
         f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;margin:0 auto;background:#ffffff;border-collapse:collapse">',
         f'<tr><td style="background:{ink};padding:28px 32px"><div style="font-family:Courier New,monospace;font-size:12px;letter-spacing:2px;color:#CDBDE6;text-transform:uppercase">WHEN Resource Hub</div>'
         f'<div style="font-family:Courier New,monospace;font-weight:bold;font-size:28px;color:#ffffff;margin-top:6px">{E(month)} selection</div></td></tr>',
         f'<tr><td style="padding:24px 32px 0;font-family:Arial,sans-serif;font-size:15px;color:{ink};line-height:1.55">Dear all,<br><br>'
         f'Here are the deadlines coming up, a few resources worth knowing and our next events.</td></tr>']
    h.append(head("Deadlines coming up"))
    if soon:
        for i in soon:
            h.append(row(i["t"], i.get("u", ""), f"Deadline {when(i)}" + (f", {i['days_left']} days left" if i.get("days_left") is not None else ""), i.get("desc", "")))
    else:
        h.append(f'<tr><td style="padding:6px 32px;font-family:Arial,sans-serif;font-size:14px;color:{muted}">There are no confirmed deadlines in the coming weeks.</td></tr>')
    h.append(head("This month's selection"))
    for label, i in picks:
        h.append(row(i["t"], i.get("u", ""), label + (f" · {i['amount']}" if i.get("amount") else ""), i.get("desc", "")))
    if fresh:
        h.append(head("New on the hub"))
        if len(fresh) <= 10:
            for i in fresh:
                h.append(row(i["t"], i.get("u", ""), i.get("c", ""), ""))
        else:
            h.append(f'<tr><td style="padding:6px 32px;font-family:Arial,sans-serif;font-size:14px;color:{ink};line-height:1.5">'
                     f'{len(fresh)} new resources this month, including help with childcare and caring costs, part-time work, '
                     f'housing advice and support for international and minority ethnic researchers.</td></tr>')
    if events:
        h.append(head("WHEN events"))
        for e in events:
            d = datetime.date.fromisoformat(e["date"]).strftime("%a %-d %B")
            h.append(row(e["title"], e.get("link", ""), f"{d}, {e.get('start', '')}", e.get("place", "")))
    h.append(f'<tr><td style="padding:28px 32px"><a href="{hub}" style="display:inline-block;background:{violet};color:#ffffff;font-family:Courier New,monospace;font-weight:bold;font-size:15px;padding:12px 20px;text-decoration:none">Open the Resource Hub</a>'
             f'<div style="font-family:Arial,sans-serif;font-size:14px;color:{muted};margin-top:14px;line-height:1.5">'
             f'<a href="{hub}deadlines.ics" style="color:{violet}">Add every deadline to your calendar</a> · '
             f'<a href="{hub}#feedback" style="color:{violet}">Did the hub help you? Tell us in one click</a></div>'
             f'<div style="font-family:Arial,sans-serif;font-size:15px;color:{ink};margin-top:22px">Best wishes,<br>The WHEN team</div></td></tr>')
    h.append('</table></body></html>')
    open("DIGEST.html", "w", encoding="utf-8").write("\n".join(h))

# ----------------------------------------------------------------------
# FEEDS (optional)
# ----------------------------------------------------------------------

def fetch_feeds():
    items = []
    if not FEEDS:
        return items
    if feedparser is None:
        print("feedparser not installed, skipping feeds", file=sys.stderr)
        return items
    for scope, url, category in FEEDS:
        parsed = feedparser.parse(url, request_headers=HEADERS)
        if getattr(parsed, "bozo", 0) and not parsed.entries:
            print(f"::warning::{url} is not a valid RSS feed", file=sys.stderr)
            continue
        for e in parsed.entries:
            title = clean(e.get("title", ""), 140)
            summary = clean(e.get("summary", ""), 160)
            blob = (title + " " + summary).lower()
            if not any(k in blob for k in KEYWORDS) or any(x in blob for x in EXCLUDE):
                continue
            items.append({
                "t": title, "u": e.get("link", ""), "c": category, "s": "All stages",
                "scope": scope, "cost": "Free", "day": "", "mon": "Open", "window": "Open",
                "desc": summary or "New fellowship listing.", "tags": ["fellowship", "auto"],
                "source": "auto", "status": "review",
            })
    return items

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    try:
        curated = json.load(open("curated.json", encoding="utf-8"))
    except FileNotFoundError:
        print("::warning::curated.json not found", file=sys.stderr)
        curated = []
    try:
        state = json.load(open("watch_state.json", encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    changes, dead = [], []
    for item in curated:
        apply_deadline(item)
        item.setdefault("added", TODAY.isoformat())
        url = item.get("u", "")
        needs_page = (CHECK_LINKS or (WATCH_PAGES and item.get("c") in WATCH_CATEGORIES)) and url.startswith("http")
        r = get(url) if needs_page else None
        if CHECK_LINKS and needs_page:
            # 401, 403 and 429 usually mean the site blocks robots, not that the page is gone
            alive = r is not None and (r.status_code < 400 or r.status_code in (401, 403, 429))
            item["link_ok"] = alive
            if not alive:
                dead.append(item)
                print(f"::warning::Link may be broken: {item.get('t')} -> {url}", file=sys.stderr)
        if WATCH_PAGES and item.get("c") in WATCH_CATEGORIES and r is not None and r.status_code < 400:
            fp, sample = page_fingerprint(r.text)
            old = state.get(url, {}).get("hash")
            if old and old != fp:
                changes.append((item, sample))
            state[url] = {"hash": fp, "seen": TODAY.isoformat()}

    # closing-soon items first, then open deadlines by date, then the rest
    order = {"soon": 0, "open": 1, "window": 2, "closed": 3}
    curated.sort(key=lambda i: (order.get(i.get("dl"), 2), i.get("deadline") or "9999"))

    seen = {norm_key(i) for i in curated}
    merged, added = list(curated), 0
    for item in fetch_feeds():
        k = norm_key(item)
        if k and k not in seen and added < MAX_AUTO_ITEMS:
            seen.add(k)
            merged.append(item)
            added += 1

    json.dump({"updated": TODAY.isoformat(), "count": len(merged), "auto_added": added,
               "resources": merged}, open("resources.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(state, open("watch_state.json", "w", encoding="utf-8"), indent=1, sort_keys=True)
    write_calendar(curated)
    write_digest(curated)

    # A short report for the GitHub Issue (only written when there is something to check)
    lines = []
    soon = [i for i in curated if i.get("dl") == "soon"]
    if changes:
        lines.append("## Pages that changed this week\n")
        lines.append("The dates or deadlines on these official pages have changed. "
                     "Open each one and, if a new round is announced, update `deadline` "
                     "(format YYYY-MM-DD) in `curated.json`.\n")
        for item, sample in changes:
            lines.append(f"- [ ] **{item['t']}**: {item['u']}")
            for s in sample[:3]:
                lines.append(f"    > {s[:200]}")
    if soon:
        lines.append("\n## Closing soon\n")
        for i in soon:
            lines.append(f"- {i['t']}: closes {i['deadline']} ({i['days_left']} days left)")
    if dead:
        lines.append("\n## Links to check\n")
        for i in dead:
            lines.append(f"- {i['t']}: {i['u']}")
    open("CHANGES.md", "w", encoding="utf-8").write("\n".join(lines) + ("\n" if lines else ""))

    print(f"resources.json: {len(merged)} items, {len(changes)} pages changed, "
          f"{len(soon)} closing soon, {len(dead)} links to check")


if __name__ == "__main__":
    main()
