# Scraper 2 — Luma Tech Category Events

The second Scraper Studio collector built for CampusHorizon. This file documents
the scraper's full lifecycle: what it does, how it was built, what broke,
how it was repaired, and the exact data contract the Django normalizer will
parse.

---

## 1. Overview

| Property | Value |
|---|---|
| Source | Luma (`luma.com`) |
| Target URL | `https://luma.com/tech` |
| Collector ID | `c_mt09dzgd2mai4o8bhu` |
| Name | `luma-tech-categories` |
| Status | ✅ **Live & verified** (Aug 19, 2026) |
| Architecture | **Single-stage Discovery** — extracts everything from the listing page cards; no navigation to individual event pages |
| Output | Flat array of event objects |
| Extracted data | title, date, location, url |
| Why Luma | Tech event listings for students; no pre-built Bright Data scraper exists → valid long-tail target |

**What the dashboard gets:** Tech events (hackathons, meetups, job fairs, workshops) with countdown-able dates, location for online/in-person filtering, and direct event URLs — everything the student lens needs (free, online, deadline < 7 days).

---

## 2. Timeline — the full incident flow

### 2.1 Create (2026-08-19 15:41 UTC)

```bash
npx -p @brightdata/cli bdata scraper create https://luma.com/tech \
  "SINGLE-STAGE extraction from this tech category page. Wait for event cards to fully render (SPA with infinite scroll). From each visible event card, extract: event_title, event_date (e.g., 'Aug 19, 2026'), event_time (e.g., '6:00 PM'), location (Online or city name), event_url. Do NOT navigate to detail pages. Handle infinite scroll to load all events." \
  --name luma-tech-categories --pretty -o tmp/luma_tech_cat_create.json
```

**Result:** generation completed in ~280 poll attempts (~15 minutes).
`collector_id: c_mt09dzgd2mai4o8bhu`, status `done`, view URL
`https://brightdata.com/cp/scrapers/c_mt09dzgd2mai4o8bhu`.

**Generated architecture (single-stage):**

- **Entry (Discovery) stage** — interaction code waits for event cards to render, extracts all fields directly from listing page
- **Parser**: extracts `event_title`, `event_date`, `location`, `event_url` from each card
- No navigation to individual event pages (single-stage design)

### 2.2 First run → Success

```bash
npx -p @brightdata/cli bdata scraper run c_mt09dzgd2mai4o8bhu https://luma.com/tech --pretty -o tmp/luma_tech_cat_sample.json
```

- Batch mode completed with **17 events**, all fields populated.
- Subsequent run returned **5 events** (current live events on the page).

**No incidents** — single-stage design with explicit wait selectors worked on first generation.

---

## 3. Issues & solutions summary

| # | Issue | Root cause | Solution |
|---|---|---|---|
| — | None | Single-stage design with explicit prompt avoided SPA rendering issues | N/A |

---

## 4. Example input & output

### 4.1 Inputs

**Create description:** "SINGLE-STAGE extraction from this tech category page. Wait for event cards to fully render (SPA with infinite scroll). From each visible event card, extract: event_title, event_date (e.g., 'Aug 19, 2026'), event_time (e.g., '6:00 PM'), location (Online or city name), event_url. Do NOT navigate to detail pages. Handle infinite scroll to load all events."

**Run command:**

```bash
npx -p @brightdata/cli bdata scraper run c_mt09dzgd2mai4o8bhu https://luma.com/tech --pretty -o tmp/luma_tech_cat_final.json
```

### 4.2 Output (real sample, 2026-08-19)

Flat array of event objects:

```json
{
  "event_title": "JEWEL CITY HACKS 5.0",
  "event_date": "26/9",
  "location": "Glendale, CA",
  "event_url": "https://luma.com/jewelcityhacks5",
  "product_page_url": "https://luma.com/jewelcityhacks5",
  "input": { "url": "https://luma.com/tech" }
}
```

All 5 events from latest run:

| # | Title | Date | Location | URL |
|---|---|---|---|---|
| 1 | JEWEL CITY HACKS 5.0 | 26/9 | Glendale, CA | `luma.com/jewelcityhacks5` |
| 2 | Pasadena Climate Happy Hour | 27/9 | Pasadena, CA | `luma.com/1fk9ei17` |
| 3 | LA Social & Tech Meetup (POTLUCK) | 29/9 | Pasadena, CA | `luma.com/i8irgkrv` |
| 4 | Tech Job Fair | 24/9 | Glendale, CA | `luma.com/7rn7202u` |
| 5 | The Water-Energy Nexus: Pasadena Edition | 14/9 | Pasadena, CA | `luma.com/0mj6hae0` |

Full sample: `tmp/luma_tech_cat_final.json`.

---

## 5. Data contract for the normalizer

| Scraper field | Type | Normalized `Event` field | Notes |
|---|---|---|---|
| `event_title` | string | `title` | |
| `event_date` | string `"DD/MM"` | `deadline` | parse day/month → ISO (assume current year) |
| `location` | string | `is_online` | `"Online"` → True, else city name |
| `event_url` | string | `url` | also the dedup key |
| `product_page_url` | string | (same as url) | |
| `input.url` | string | (source tracking) | `https://luma.com/tech` |

**Normalizer steps:** iterate flat array → drop empty/invalid → parse `event_date` (DD/MM) to ISO datetime → map fields → upsert by `event_url`.

---

## 6. Runbook references

- `AGENTS.md` — pinned Collector ID table (§ Pinned Collector IDs)
- `SCRAPER_SETUP.md` — generic per-source process + troubleshooting lessons
- `tmp/luma_tech_cat_create.json` — create response envelope
- `tmp/luma_tech_cat_final.json` — verified run output (5 events, all fields)

---

## 7. Notes for future maintenance

- **Page-specific selectors:** This scraper's template has selectors tuned for `https://luma.com/tech`. Running on other category pages (`/ai`, `/crypto`, `/climate`) will fail with `wait_element_timeout`.
- **If Luma redesigns `/tech`:** Run `bdata scraper heal c_mt09dzgd2mai4o8bhu "<what broke>" --auto-approve --auto-save`
- **Date format:** Current output uses `DD/MM` (e.g., "26/9"). Normalizer should assume current year and parse accordingly.
- **Event count varies:** The `/tech` page shows current/upcoming events only. Count will fluctuate (5–20 typical).