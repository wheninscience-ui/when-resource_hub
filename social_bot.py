"""
WHEN Resource Hub, weekly social posts.

Every Monday, after update_resources.py:
  1. picks the Resource of the Week (the same one the website shows);
  2. picks deadlines closing in the next 14 days that have not been posted yet;
  3. draws a card image for each post (1200 x 630, in the hub's style);
  4. posts to Bluesky, if BSKY_HANDLE and BSKY_APP_PASSWORD are set as repository secrets;
  5. writes SOCIAL.md with the same posts, ready to paste on LinkedIn.

Without the secrets it runs as a dry run: it only writes SOCIAL.md and the images in social/.
"""

import datetime
import json
import os
import sys
import urllib.request

import requests
from PIL import Image, ImageDraw, ImageFont

SITE = "https://wheninscience-ui.github.io/when-resource_hub/"
RAW = "https://raw.githubusercontent.com/wheninscience-ui/when-resource_hub/main/"
HASHTAG = "WHENResourceOfTheWeek"
ROTW_CATS = {"Fellowships and awards", "Funding opportunities", "Help with costs",
             "Mentoring schemes", "Leadership programmes"}
STATE_FILE = "bluesky_state.json"
TODAY = datetime.date.today()
PDS = "https://bsky.social/xrpc"

INK, VIOLET, LILAC, PINK, WHITE = (44, 26, 71), (124, 58, 237), (232, 222, 243), (240, 171, 252), (255, 255, 255)

# ---------------------------------------------------------------------- data

def load():
    data = json.load(open("resources.json", encoding="utf-8"))
    return data["resources"]

def monday(d):
    return d - datetime.timedelta(days=d.weekday())

def resource_of_the_week(items):
    """Same rule as the website: a fixed pool sorted by title, rotating by week number."""
    pool = sorted([r for r in items if r.get("source") != "auto" and r.get("status") != "review"
                   and r.get("c") in ROTW_CATS], key=lambda r: r["t"])
    if not pool:
        return None
    mon = monday(TODAY)
    for r in pool:
        if r.get("rotw") and monday(datetime.date.fromisoformat(r["rotw"])) == mon:
            return r
    mon_ms = int(datetime.datetime(mon.year, mon.month, mon.day, tzinfo=datetime.timezone.utc).timestamp() * 1000)
    return pool[(mon_ms // (7 * 24 * 3600 * 1000)) % len(pool)]

def closing_soon(items, state):
    out = []
    for r in items:
        if r.get("dl") in ("open", "soon") and r.get("days_left") is not None and 0 < r["days_left"] <= 14:
            key = r["t"] + "|" + r["deadline"]
            if key not in state.get("deadlines", []):
                out.append(r)
    return sorted(out, key=lambda r: r["deadline"])[:2]

def when_line(r):
    if r.get("dl") in ("open", "soon") and r.get("deadline"):
        d = datetime.date.fromisoformat(r["deadline"])
        return f"Deadline {d.day} {d:%B %Y}"
    w = r.get("window") or r.get("mon") or ""
    if not w or w.lower() in ("rolling",):
        return "Open all year"
    return f"Usually opens: {w}"

# ---------------------------------------------------------------------- image

def font(size, bold=True):
    """Courier Prime, as on the website, downloaded once; otherwise a monospace system font."""
    name = "CourierPrime-Bold.ttf" if bold else "CourierPrime-Regular.ttf"
    path = os.path.join("social", name)
    if not os.path.exists(path):
        try:
            os.makedirs("social", exist_ok=True)
            urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/courierprime/" + name, path)
        except Exception:
            path = None
    for p in [path, "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold
              else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap(draw, text, f, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=f) <= width:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def card(r, label, path):
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im, "RGBA")
    # the hub's motif: overlapping circles on the right
    d.ellipse((780, 120, 1100, 440), fill=VIOLET + (255,))
    d.ellipse((900, 40, 1180, 320), fill=PINK + (200,))
    d.ellipse((840, 330, 1060, 550), fill=LILAC + (170,))
    d.text((72, 64), "// " + label.upper(), font=font(26, False), fill=(205, 189, 230))
    y = 120
    for line in wrap(d, r["t"], font(56), 680)[:4]:
        d.text((72, y), line, font=font(56), fill=WHITE)
        y += 66
    y += 18
    d.rectangle((72, y + 6, 72 + 12, y + 18), fill=PINK)
    d.text((96, y - 10), when_line(r), font=font(30), fill=PINK)
    if r.get("amount"):
        d.text((96, y + 34), r["amount"], font=font(30, False), fill=LILAC)
    d.text((72, H - 78), "WHEN Resource Hub", font=font(30), fill=WHITE)
    d.text((72, H - 42), "wheninscience-ui.github.io/when-resource_hub", font=font(22, False), fill=(205, 189, 230))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "PNG", optimize=True)
    return path

# ---------------------------------------------------------------------- text

def post_text(r, kind, week):
    if kind == "rotw":
        head = f"Resource of the Week {week}: {r['t']}"
    else:
        head = f"{r['days_left']} days left: {r['t']}"
    body = r.get("desc", "")
    extra = [when_line(r)] + ([r["amount"]] if r.get("amount") else [])
    text = f"{head}\n\n{body}\n\n" + ". ".join(extra) + ".\n\nAll details on the WHEN Resource Hub.\n#" + HASHTAG
    if len(text) > 290:  # Bluesky limit is 300 characters
        body = body[: max(0, len(body) - (len(text) - 287))].rsplit(" ", 1)[0] + "..."
        text = f"{head}\n\n{body}\n\n" + ". ".join(extra) + ".\n\nAll details on the WHEN Resource Hub.\n#" + HASHTAG
    return text

# ---------------------------------------------------------------------- Bluesky

def bsky_session():
    h, p = os.environ.get("BSKY_HANDLE"), os.environ.get("BSKY_APP_PASSWORD")
    if not h or not p:
        return None
    r = requests.post(PDS + "/com.atproto.server.createSession", json={"identifier": h, "password": p}, timeout=30)
    r.raise_for_status()
    return r.json()

def bsky_post(sess, text, url, title, desc, image_path):
    auth = {"Authorization": "Bearer " + sess["accessJwt"]}
    with open(image_path, "rb") as f:
        up = requests.post(PDS + "/com.atproto.repo.uploadBlob", data=f.read(),
                           headers={**auth, "Content-Type": "image/png"}, timeout=60)
    up.raise_for_status()
    b = text.encode("utf-8")
    tag = ("#" + HASHTAG).encode("utf-8")
    start = b.rfind(tag)
    facets = [{"index": {"byteStart": start, "byteEnd": start + len(tag)},
               "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": HASHTAG}]}] if start >= 0 else []
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "langs": ["en"],
        "facets": facets,
        "embed": {"$type": "app.bsky.embed.external",
                  "external": {"uri": url, "title": title[:300], "description": desc[:300],
                               "thumb": up.json()["blob"]}},
    }
    r = requests.post(PDS + "/com.atproto.repo.createRecord", headers=auth, timeout=30,
                      json={"repo": sess["did"], "collection": "app.bsky.feed.post", "record": record})
    r.raise_for_status()
    return r.json().get("uri")

# ---------------------------------------------------------------------- main

def main():
    items = load()
    try:
        state = json.load(open(STATE_FILE, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    week = TODAY.isocalendar()[1]
    posts = []
    rotw = resource_of_the_week(items)
    if rotw and state.get("rotw_week") != f"{TODAY.year}-{week}":
        posts.append(("rotw", rotw, f"Resource of the Week {week}"))
    for r in closing_soon(items, state):
        posts.append(("deadline", r, "Closing soon"))

    sess = None
    try:
        sess = bsky_session()
    except Exception as e:
        print(f"::warning::Bluesky login failed: {e}", file=sys.stderr)

    md = [f"# Posts for the week of {monday(TODAY):%d %B %Y}", "",
          "Bluesky: " + ("posted automatically." if sess else "not connected, so nothing was posted (see README)."),
          "LinkedIn: copy the text below and attach the image (right click, save image).", ""]
    for kind, r, label in posts:
        slug = "".join(c if c.isalnum() else "-" for c in r["t"].lower()).strip("-")[:40]
        img = card(r, label, f"social/{TODAY.isoformat()}-{slug}.png")
        text = post_text(r, kind, week)
        uri = None
        if sess:
            try:
                uri = bsky_post(sess, text, SITE, r["t"], r.get("desc", ""), img)
            except Exception as e:
                print(f"::warning::Bluesky post failed for {r['t']}: {e}", file=sys.stderr)
        if kind == "rotw" and (uri or not sess):
            state["rotw_week"] = f"{TODAY.year}-{week}" if uri else state.get("rotw_week")
        if kind == "deadline" and uri:
            state.setdefault("deadlines", []).append(r["t"] + "|" + r["deadline"])
        md += [f"## {label}", "", f"![{r['t']}]({RAW}{img})", "", f"Image file: `{img}`", "", "```", text.replace("All details on the WHEN Resource Hub.",
               "All details on the WHEN Resource Hub: " + SITE), "```", ""]
        print(("POSTED " + uri) if uri else ("DRAFT " + r["t"]))

    open("SOCIAL.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), indent=1)

if __name__ == "__main__":
    main()
