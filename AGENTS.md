# CampusHorizon — Project Guide for AI Agents

A student hackathon/tech-event discovery dashboard. Self-healing Bright Data
scrapers (Scraper Studio) feed a Django dashboard. If a target site redesigns,
the scraper is repaired with `bdata scraper heal` — same Collector ID, nothing
downstream breaks.

## Hackathon constraints (Scrape-Verse, ends Aug 23 2026)

- Scrape **publicly available data only**. No login-walled, paywalled, or
  personal data. No X/Twitter.
- **Only long-tail targets**: sites without a pre-built Bright Data scraper.
  Devpost, Luma, MLH, Devfolio, and LabLab confirmed absent from the Scraper
  Library. Verify any new target before adding it.
- **Documented exception — Meetup**: Meetup *does* have a pre-built Bright Data
  scraper, but the user explicitly chose a custom collector for it (control over
  fields: title, start date, venue, online flag, group name, url). Do not replace
  it with the library scraper without asking.
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
| LabLab   | `c_mt2pm82fb4ta19gqe` | `https://lablab.ai/ai-hackathons` | title, url, start/deadline dates, prize, format, tags |
| Meetup   | `c_mt2qwd9216p13lefvg` | `https://www.meetup.com/find/?source=EVENTS&categoryId=546` | title, start datetime, venue, online flag, group name, url (custom-collector exception) |

> These IDs are live production collectors. Reuse them; only run
> `bdata scraper create` for a brand-new target, then add its row above and to
> `config.py` + README.
>
> **History**: the first lablab (`c_mt2n5ie32qzka71trc`) and meetup
> (`c_mt2nb1or1052fx65zs`) collectors were replaced via the documented
> create-fallback after repeated heal failures left them extracting broken
> data (detail-page timeouts / locale-drift rows). Do not reuse the dead IDs.
> Also dead: Devfolio v1 (`c_mt0y01c02c02v5dei1`, superseded by v2) and an
> unfinished lablab build (`c_mt2rsnuh2r56c9y6y4`, AI generation failed).
> The CLI cannot list/rename/delete collectors — cleanup is manual in the
> Bright Data dashboard; never delete the six pinned IDs above.

## Project layout

```
manage.py
campushorizon/            # Django project
events/                   # Django app
  models.py               # Event, EventSnapshot, Source
  scraper/
    config.py             # collector IDs, target URLs, field mappings
    client.py             # Bright Data API: POST /dca/trigger, GET /dca/dataset, POST refactor_template
    normalizer.py         # per-source raw payload → unified Event schema
    validator.py          # health rules (R0 empty, R1 zero records, R3 missing fields)
    archive.py            # raw run archive + manifests
  management/commands/
    collect_events.py     # offline samples or --online live trigger → normalize → upsert + snapshot
    heal_check.py         # detect breakage; --auto-heal triggers refactor_template
  views.py, templates/    # dashboard: feed, filters, countdown badges
static/                   # Tailwind + Chart.js assets
.github/workflows/
  ci.yml                  # tests on push
  collect.yml             # nightly live collection + auto-heal + raw artifact
.env.example              # template; real .env stays gitignored
README.md
```

## Common commands

```bash
python manage.py runserver
python manage.py collect_events               # offline from tmp/ samples (default)
python manage.py collect_events --online      # trigger live collectors via API (needs BRIGHT_DATA_API_TOKEN)
python manage.py heal_check                   # detect stale/empty extraction
python manage.py heal_check --auto-heal       # + trigger heal API for broken sources (approve still via CLI)
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
3. Trigger the heal — CLI (interactive) or `heal_check --auto-heal` (cron/API):
   `bdata scraper heal <COLLECTOR_ID> "<plain-language description of what broke>"`
4. `bdata scraper approve <COLLECTOR_ID>` — approval is always manual, even after an auto-heal.
5. Re-run `collect_events --online` → dashboard recovers. Same Collector ID, no code change downstream.
6. If heal can't fix it, fall back to `bdata scraper create` and update `config.py` + this file.

## Do / Don't

- DO reuse pinned Collector IDs; only create a scraper when the target is new.
- DO verify new targets aren't in Bright Data's pre-built library first.
- DO keep `.env` out of every command output and commit.
- DON'T scrape login-walled, paywalled, or personal data.
- DON'T use the Bright Data dashboard as a workflow step.
- DON'T add sources without updating `config.py`, this file, and the README.
- DO keep `client.py`'s API surface small: trigger, dataset fetch, refactor_template only.
