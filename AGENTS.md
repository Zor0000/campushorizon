# CampusHorizon — Project Guide for AI Agents

A student hackathon/tech-event discovery dashboard. Self-healing Bright Data
scrapers (Scraper Studio) feed a Django dashboard. If a target site redesigns,
the scraper is repaired with `bdata scraper heal` — same Collector ID, nothing
downstream breaks.

## Hackathon constraints (Scrape-Verse, ends Aug 23 2026)

- Scrape **publicly available data only**. No login-walled, paywalled, or
  personal data. No X/Twitter.
- **Only long-tail targets**: sites without a pre-built Bright Data scraper.
  Devpost, Luma, MLH, and Devfolio confirmed absent from the Scraper Library.
  Verify any new target before adding it.
- **Never commit or print secrets**: `.env` is gitignored. Mask tokens in demos.
- The terminal is the UI: drive everything through the Bright Data CLI, not the dashboard.
- Every change must keep the pipeline reproducible: a judge can clone and run it.

## Bright Data CLI (the source of truth)

Run via npx — no global install:

```bash
npx -p @brightdata/cli bdata login                 # OAuth, once
npx -p @brightdata/cli bdata scraper create <URL> "<data you need>"
npx -p @brightdata/cli bdata scraper run   <COLLECTOR_ID> <URL> --pretty
npx -p @brightdata/cli bdata scraper heal   <COLLECTOR_ID> "<what broke>"
npx -p @brightdata/cli bdata scraper approve <COLLECTOR_ID>      # or --reject
```

- `bdata scraper create` takes 5–15 min (up to 25 for complex sites).
- Always `--pretty` when inspecting output JSON.

## Pinned Collector IDs — REUSE, NEVER REBUILD

These are production endpoints. The agent must reuse them, not re-create scrapers.

| Source   | Collector ID | Target URL               | Data                                     |
|----------|--------------|--------------------------|------------------------------------------|
| Devpost  | `c_msz1ehqzhdlpeq7og` | `https://devpost.com/hackathons` | title, deadline, prizes, tags, online, url |
| Luma     | `c_mt09dzgd2mai4o8bhu` | `https://luma.com/tech` | title, date, location, url |
| MLH      | `c_mt0hfqqi1q7jk1sdbo` | `https://mlh.io/events`  | event_name, start_date, end_date, location, event_type, event_url |
| Devfolio | `c_mt0y94lp18i9rcuhhv` | `https://devfolio.co/hackathons` | hackathon_name, submission_deadline, prize_amount, product_page_url |

> **TODO (setup day 1):** run `bdata scraper create` for each target and fill
> in the IDs above. Until filled, do not guess; ask the user.

## Project layout

```
manage.py
campushorizon/            # Django project
events/                   # Django app
  models.py               # Event, EventSnapshot, Source
  scraper/
    config.py             # collector IDs, target URLs, field mappings
    client.py             # POST /dca/trigger + fetch results
  management/commands/
    collect_events.py     # trigger collectors → normalize → upsert + snapshot
    heal_check.py         # empty extraction → suggest bdata scraper heal
  views.py, templates/    # dashboard: feed, filters, countdown badges
static/                   # Tailwind + Chart.js assets
.github/workflows/collect.yml   # cron pipeline (fresh data, no humans)
.env.example              # template; real .env stays gitignored
README.md
```

## Common commands

```bash
python manage.py runserver
python manage.py collect_events        # trigger all collectors, upsert events
python manage.py heal_check           # detect stale/empty extraction
python manage.py test events
```

## Conventions

- Python 3.12+, Django 5.x, SQLite (no external DB for MVP).
- Unified `Event` model: normalize every source into the same schema
  (title, source, deadline, prizes, tags, is_online, url).
- Snapshot on every collect → powers "new this week" diffs and deadline changes.
- UI: Django templates + Tailwind + Chart.js. Student lens on everything:
  free, online, deadline < 7 days filters.
- No comments unless the code needs an explanation; follow Django best practice.

## Self-healing workflow (the hero demo)

1. Site changes layout → collector returns empty/missing fields.
2. Run `heal_check` or inspect run output to confirm the breakage.
3. `bdata scraper heal <COLLECTOR_ID> "<plain-language description of what broke>"`
4. `bdata scraper approve <COLLECTOR_ID>`
5. Re-run `collect_events` → dashboard recovers. Same Collector ID, no code change downstream.
6. If heal can't fix it, fall back to `bdata scraper create` and update `config.py` + this file.

## Do / Don't

- DO reuse pinned Collector IDs; only create a scraper when the target is new.
- DO verify new targets aren't in Bright Data's pre-built library first.
- DO keep `.env` out of every command output and commit.
- DON'T scrape login-walled, paywalled, or personal data.
- DON'T use the Bright Data dashboard as a workflow step.
- DON'T add sources without updating `config.py`, this file, and the README.
