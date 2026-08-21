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

- **Hackathons** (Devpost, MLH, Devfolio, LabLab): search, online only, has
  prizes, ending soon, include ended, per-source, sort by deadline/newest.
- **Tech Events** (Luma, Meetup): search, starting soon, include ended,
  per-source, sort. No prize/online filters — those events don't carry
  comparable prize data.
- Everything is category-aware: prize rows are never rendered for tech events,
  and MLH badges read "Starts in Xd" (its date is a start date, not a deadline).

## Live collection (online mode)

`collect_events` runs offline by default so anyone can clone and run it. With a
Bright Data API token it triggers the real collectors and imports fresh data:

```bash
cp .env.example .env          # then paste your token from
                              # https://brightdata.com/cp/setting → API Tokens
python manage.py collect_events --online   # trigger → poll → upsert + snapshot
python manage.py heal_check --auto-heal    # detect breakage, auto-trigger heal
```

- `--online` triggers all 6 pinned collectors via `POST /dca/trigger`, polls
  `GET /dca/dataset` (30s interval, 25 min timeout per collector, configurable
  with `--poll-timeout`), archives raw payloads to `raw/<run_id>` (manifest
  `mode: online`), then normalizes + upserts as usual.
- `heal_check --auto-heal` calls the same self-healing endpoint the CLI uses
  (`POST /dca/collectors/{id}/refactor_template`) for any source with ERROR
  issues. **Approval stays manual**: `npx -p @brightdata/cli bdata scraper approve <COLLECTOR_ID>`.
- GitHub Actions runs this nightly (`.github/workflows/collect.yml`, 06:00 UTC)
  and on demand via **Actions → Collect → Run workflow**. Add the token as a
  repo secret named `BRIGHT_DATA_API_TOKEN`. Fresh payloads are uploaded as the
  `raw-runs` artifact on every run.

## Architecture

```
manage.py
campushorizon/            # Django project
events/                   # Django app
  models.py               # Event, EventSnapshot, Source
  scraper/
    config.py             # collector IDs, target URLs, field mappings
    client.py             # Bright Data API: trigger /dca/trigger, fetch /dca/dataset, heal refactor_template
    normalizer.py         # per-source raw payload → unified Event schema
    validator.py          # health rules (R0 empty, R1 zero records, R3 missing fields)
    archive.py            # raw run archive + manifests
  management/commands/
    collect_events.py     # offline samples or --online live trigger → normalize → upsert + snapshot
    heal_check.py         # health check → --auto-heal via refactor_template
  views.py, templates/    # dashboard: feed, category filters, countdown badges
tmp/*.json                # sample payloads (committed for offline repro)
.env.example              # BRIGHT_DATA_API_TOKEN template (real .env is gitignored)
.github/workflows/
  ci.yml                  # tests on push — judge can clone and run
  collect.yml             # nightly live collection + auto-heal + raw artifact
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
| LabLab   | `c_mt2pm82fb4ta19gqe` | https://lablab.ai/ai-hackathons | title, url, start/deadline dates, prize, format, tags |
| Meetup   | `c_mt2qwd9216p13lefvg` | https://www.meetup.com/find/?source=EVENTS&categoryId=546 | title, start datetime, venue, online flag, group name, url |

> **Meetup exception**: Meetup has a pre-built Bright Data scraper in the
> Scraper Library, but CampusHorizon deliberately uses a **custom collector**
> for field control (title, start datetime, venue, online flag, group name,
> url). All other sources are long-tail targets with no pre-built scraper.

See `SCRAPER_1_DEVPOST.md` … `SCRAPER_4_DEVFOLIO.md` and `SCRAPER_SETUP.md`
for how each collector was built and healed.

## Self-healing workflow (the hero demo)

1. Site changes layout → collector returns empty/missing fields.
2. Run `python manage.py heal_check` to confirm the breakage (in cron, add
   `--auto-heal` to trigger the heal API automatically).
3. `bdata scraper heal <COLLECTOR_ID> "<plain-language description of what broke>"`
4. `bdata scraper approve <COLLECTOR_ID>`
5. Re-run `python manage.py collect_events --online` → dashboard recovers.
   Same Collector ID, no code change downstream.

## Env vars

`.env` is optional — everything runs offline from `tmp/` without it. Only the
live path needs it: copy `.env.example` and set `BRIGHT_DATA_API_TOKEN` (used by
`collect_events --online` and `heal_check --auto-heal`). `.env` is gitignored,
never commit it.