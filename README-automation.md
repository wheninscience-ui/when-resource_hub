# WHEN Resource Hub - setup and automatic updates

## Files

| File | What it is | You edit it? |
|------|------------|--------------|
| `index.html` | The website (rename `when-resource-hub.html` to this) | rarely |
| `curated.json` | Your hand-picked core resources. The quality-controlled list. | yes, often |
| `resources.json` | What the site actually loads. Generated automatically. | no, leave it to the bot |
| `update_resources.py` | The script that builds `resources.json` | only to add feeds |
| `.github/workflows/update-resources.yml` | The 48-hour schedule | rarely |

## How the automatic update works

A static site on GitHub Pages has no server, so it cannot fetch and refresh on its own.
Instead, a scheduled GitHub Action does the work for it:

1. Every 48 hours GitHub runs `update_resources.py`.
2. The script keeps everything in `curated.json`, then pulls new fellowship
   listings from the RSS feeds you set, filters and de-duplicates them.
3. It writes `resources.json` and commits it back to the repo.
4. The site loads `resources.json` on every visit, so visitors always see the
   latest list. If the file is missing, the site falls back to its built-in list.

Auto-fetched items are marked `"source": "auto"` and `"status": "review"` so you
can see at a glance which entries a human has not yet checked. Promote the good
ones into `curated.json` and they become permanent.

## One-time setup

1. Rename `when-resource-hub.html` to `index.html`.
2. In your repo, place the files like this:
   ```
   index.html
   curated.json
   resources.json
   update_resources.py
   .github/workflows/update-resources.yml
   ```
   (Create the `.github/workflows/` folders and put the yml file inside.)
3. Settings > Pages > Deploy from a branch > `main` > `/ (root)`.
4. Settings > Actions > General > Workflow permissions > set to
   "Read and write permissions" (so the bot can commit).
5. Open the Actions tab, pick "Update WHEN resources", and click "Run workflow"
   once to test it.

## Choosing your feeds

Open https://www.jobs.ac.uk/feeds, pick a subject area or job type, and copy the
RSS link. Paste it into the `FEEDS` list near the top of `update_resources.py`:

```python
FEEDS = [
    ("UK", "PASTE_RSS_URL_HERE", "Fellowships and awards"),
]
```

You can add several feeds (different subjects, EURAXESS, university boards). The
`KEYWORDS` and `EXCLUDE` lists control which listings are kept.

## Honest limitations

- Feed quality varies. RSS gives titles, links and short summaries, not clean
  deadlines or eligibility, so auto items are rougher than curated ones. That is
  why they land in a review state rather than going live polished.
- If a feed changes its format or URL, that feed silently returns nothing. The
  curated list always still shows, so the site never breaks.
- The link checker flags dead curated links in the Action log. It does not delete
  them, so you decide what to fix.
- "Find every fellowship automatically" is not realistic from open feeds alone.
  Treat the automation as a steady stream of candidates plus a safety net for
  stale links, with your curation as the real quality layer.
