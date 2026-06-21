# WHEN Resource Hub

A curated, searchable home for the funding, fellowships, mentoring and wellbeing resources that women and underrepresented people in academia need, gathered in one place and kept current.

**Live site** &nbsp;https://wheninscience-ui.github.io/when-resource_hub/

Built for the Women in Higher Education Network (WHEN).

## What's inside

- `index.html` (the site, a single file, no build step)
- `curated.json` (the hand-picked core resources)
- `resources.json` (what the site loads, refreshed automatically)
- `update_resources.py` (the updater script)
- `.github/workflows/update-resources.yml` (runs every 48 hours)
- `README-automation.md` (full setup and how the automation works)

## Updating resources

Edit `curated.json` to add or change a resource. Every 48 hours a GitHub Action pulls new fellowship listings, refreshes `resources.json`, and the site updates itself. Auto-fetched items are marked for review so a human stays in the loop. Details are in `README-automation.md`.

## Credits

Women in Higher Education Network (WHEN), Queen Mary University of London.
