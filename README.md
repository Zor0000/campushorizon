# CampusHorizon

Student hackathon / tech-event discovery dashboard. Self-healing Bright Data
scrapers (Scraper Studio) feed a Django dashboard. If a target site redesigns,
the scraper is repaired with `bdata scraper heal` — same Collector ID, nothing
downstream breaks.

Built for the Scrape-Verse hackathon (ends Aug 23 2026). Scrapes **publicly
available data only** — no login-walled, paywalled, or personal data.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collect_events        # loads sample data from tmp/ (offline)
python manage.py runserver
```

- Dashboard: http://localhost:8000/ → Hackathons / Tech Events
- Run tests: `python manage.py test events`

`collect_events` runs in offline mode by default and reads the sample payloads
in `tmp/`. It upserts into the `Event` model and snapshots every event into
`EventSnapshot` (powers "new this week" diffs and deadline changes).

## Filters

- **Hackathons** (Devpost, MLH, Devfolio): search, online only, has prizes,
  ending soon, include ended, per-source, sort by deadline/newest.
- **Tech Events** (Luma): search, starting soon, include ended, per-source,
  sort. No prize/online filters — Luma events don't carry that data.
- Everything is category-aware: prize rows are never rendered for tech events,
  and MLH badges read "Starts in Xd" (its date is a start date, not a deadline).

## Architecture

```
manage.py
campushorizon/            # Django project
events/                   # Django app
  models.py               # Event, EventSnapshot, Source
  scraper/
    config.py             # collector IDs, target URLs, field mappings
    normalizer.py         # per-source raw payload → unified Event schema
    validator.py          # health rules (R0 empty, R1 zero records, R3 missing fields)
    archive.py            # raw run archive + manifests
  management/commands/
    collect_events.py     # load samples → normalize → upsert + snapshot
    heal_check.py         # empty extraction → suggest bdata scraper heal
  views.py, templates/    # dashboard: feed, category filters, countdown badges
tmp/*.json                # sample payloads (committed for offline repro)
.github/workflows/ci.yml  # tests on push — judge can clone and run
```

## Bright Data CLI (the source of truth)

```bash
npx -p @brightdata/cli bdata login                 # OAuth, once
npx -p @brightdata/cli bdata scraper run   <COLLECTOR_ID> <URL> --pretty
npx -p @brightdata/cli bdata scraper heal   <COLLECTOR_ID> "<what broke>"
npx -p @brightdata/cli bdata scraper approve <COLLECTOR_ID>      # or --reject
```

Pinned Collector IDs (reuse, never rebuild):

| Source   | Collector ID | Target URL               | Data                                     |
|----------|--------------|--------------------------|------------------------------------------|
| Devpost  | `c_msz1ehqzhdlpeq7og` | https://devpost.com/hackathons | title, deadline, prizes, tags, online, url |
| Luma     | `c_mt09dzgd2mai4o8bhu` | https://luma.com/tech | title, date, location, url |
| MLH      | `c_mt0hfqqi1q7jk1sdbo` | https://mlh.io/events  | event_name, start_date, end_date, location, event_type, event_url |
| Devfolio | `c_mt0y94lp18i9rcuhhv` | https://devfolio.co/hackathons | hackathon_name, submission_deadline, prize_amount, product_page_url |

See `SCRAPER_1_DEVPOST.md` … `SCRAPER_4_DEVFOLIO.md` and `SCRAPER_SETUP.md`
for how each collector was built and healed.

## Self-healing workflow (the hero demo)

1. Site changes layout → collector returns empty/missing fields.
2. Run `python manage.py heal_check` to confirm the breakage.
3. `bdata scraper heal <COLLECTOR_ID> "<plain-language description of what broke>"`
4. `bdata scraper approve <COLLECTOR_ID>`
5. Re-run `python manage.py collect_events` → dashboard recovers. Same
   Collector ID, no code change downstream.

## Env vars

`.env` is optional in this repo (everything runs offline from `tmp/`). If the
online trigger path (`events/scraper/client.py`) is added later, put the Bright
Data API token in `.env` — it is gitignored, never commit it.