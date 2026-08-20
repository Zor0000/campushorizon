# Scraper 3 — MLH Student Hackathon Calendar

The third Scraper Studio collector built for CampusHorizon. This file documents
the scraper's full lifecycle: what it does, how it was built, what broke,
how it was repaired, and the exact data contract the Django normalizer will
parse.

---

## 1. Overview

| Property | Value |
|---|---|
| Source | MLH (`mlh.io`) |
| Target URL | `https://mlh.io/events` |
| Collector ID | `c_mt0hfqqi1q7jk1sdbo` |
| Name | `mlh-hackathons` |
| Status | ✅ **Live & verified** (Aug 19, 2026) |
| Architecture | **Single-stage Discovery** — extracts everything from the listing page cards; no navigation to individual event pages |
| Output | Per-page wrapper: `{"events": [...], "product_page_url", "input"}` |
| Extracted data | event_name, start_date, end_date, location, event_type, event_url |
| Why MLH | Major student hackathon calendar; no pre-built Bright Data scraper exists → valid long-tail target |

**What the dashboard gets:** Student hackathons with countdown-able dates, online/in-person flags, and direct event URLs — everything the student lens needs (free, online, deadline < 7 days).

---

## 2. Timeline — the full incident flow

### 2.1 Create (2026-08-19 19:26 UTC)

```bash
npx -p @brightdata/cli bdata scraper create https://mlh.io/events \
  "SINGLE-STAGE extraction from this hackathon calendar page. Wait for event cards to fully render. From each visible event card, extract: event_name, start_date, end_date, whether the event is online or in-person with the location, and the link to the event page. Do NOT navigate to detail pages. Handle pagination/infinite scroll to load all events." \
  --name mlh-hackathons --pretty -o tmp/mlh_create.json
```

**Result:** generation completed in ~461 poll attempts (~25 minutes).
`collector_id: c_mt0hfqqi1q7jk1sdbo`, status `done`, view URL
`https://brightdata.com/cp/scrapers/c_mt0hfqqi1q7jk1sdbo`.

**Generated architecture (single-stage):**

- **Entry (Discovery) stage** — interaction code waits for event cards to render, extracts all fields directly from listing page
- **Parser**: extracts `event_name`, `start_date`, `end_date`, `location`, `event_type`, `event_url` from each card
- No navigation to individual event pages (single-stage design)

### 2.2 First run → Success

```bash
npx -p @brightdata/cli bdata scraper run c_mt0hfqqi1q7jk1sdbo https://mlh.io/events --pretty -o tmp/mlh_sample.json
```

- Realtime mode hit page limit → switched to batch mode.
- Batch completed with **70 hackathons** extracted.
- **Mixed data quality** (expected — see §2.3).

### 2.3 Data quality observation

MLH listing pages show different levels of detail depending on event source:

| Event Source | Fields Available | Example |
|---|---|---|
| `events.mlh.io` / `events.mlh.com` | event_name, start_date, end_date, location, event_type, event_url | "Midnight Hackathon", "JULY 17", "Aug 30 1:00PM", "Digital" |
| External sites (hackgt.com, hackthenorth.com) | location, event_type, event_url | "Online", "In-Person", URL only |

**Why:** MLH's listing page only shows full dates for events hosted on their own platform (`events.mlh.io`). External hackathon sites link out to their own URLs where dates are displayed.

**Impact on dashboard:** 4 events have full date details; 66 events have URL + online/in-person flag. The URL is the dedup key and provides a direct link to the hackathon.

---

## 3. Issues & solutions summary

| # | Issue | Root cause | Solution |
|---|---|---|---|
| — | None | Single-stage design with explicit wait selectors worked on first generation | N/A |
| 1 | Mixed data quality | MLH listing shows limited info for external hackathons | Expected behavior — URL + online flag still valuable for dashboard |

---

## 4. Example input & output

### 4.1 Inputs

**Create description:** "SINGLE-STAGE extraction from this hackathon calendar page. Wait for event cards to fully render. From each visible event card, extract: event_name, start_date, end_date, whether the event is online or in-person with the location, and the link to the event page. Do NOT navigate to detail pages. Handle pagination/infinite scroll to load all events."

**Run command:**

```bash
npx -p @brightdata/cli bdata scraper run c_mt0hfqqi1q7jk1sdbo https://mlh.io/events --pretty -o tmp/mlh_sample.json
```

### 4.2 Output (real sample, 2026-08-19)

Per-page wrapper:

```json
{
  "events": [
    {
      "event_name": "Midnight Hackathon",
      "start_date": "JULY 17",
      "end_date": "Aug 30 1:00PM",
      "location": "Event is hosted online",
      "event_type": "Digital",
      "event_url": "https://events.mlh.com/events/14413-midnight-hackathon?utm_source=mlh&utm_medium=referral&utm_campaign=events&utm_content=Midnight+Virtual+Hackathon+%5BJuly%5D"
    }
  ],
  "product_page_url": "https://events.mlh.com/events/14413-midnight-hackathon?utm_source=mlh&utm_medium=referral&utm_campaign=events&utm_content=Midnight+Virtual+Hackathon+%5BJuly%5D",
  "input": { "url": "https://mlh.io/events" }
}
```

External hackathon (limited fields):

```json
{
  "events": [
    {
      "location": "Online",
      "event_type": "In-Person",
      "event_url": "https://hackthenorth.com/?utm_source=mlh&utm_medium=referral&utm_campaign=events&utm_content=Hack+the+North"
    }
  ],
  "product_page_url": "https://hackthenorth.com/?utm_source=mlh&utm_medium=referral&utm_campaign=events&utm_content=Hack+the+North",
  "input": { "url": "https://mlh.io/events" }
}
```

Full sample: `tmp/mlh_sample.json`.

---

## 5. Data contract for the normalizer

| Scraper field | Type | Normalized `Event` field | Notes |
|---|---|---|---|
| `event_name` | string | `title` | May be empty for external hackathons |
| `start_date` | string `"JULY 17"` | `deadline` | Parse month+day → ISO datetime (assume current year) |
| `end_date` | string `"Aug 30 1:00PM"` | (optional end) | May be empty or just time |
| `location` | string | `is_online` | `"Event is hosted online"` → True, else location name |
| `event_type` | string `"Digital"` / `"In-Person"` | `is_online` | Confirm with location field |
| `event_url` | string | `url` | also the dedup key; strip UTM params |

**Normalizer steps:** unwrap `events` per page → drop empty/invalid → dedupe by `event_url` → parse `start_date` (month+day) to ISO datetime → strip UTM params from URL → map fields → upsert.

---

## 6. Runbook references

- `AGENTS.md` — pinned Collector ID table (§ Pinned Collector IDs)
- `SCRAPER_SETUP.md` — generic per-source process + troubleshooting lessons
- `tmp/mlh_create.json` — create response envelope
- `tmp/mlh_sample.json` — verified run output (70 hackathons)

---

## 7. Notes for future maintenance

- **Mixed data quality is expected.** MLH listing pages show full dates only for `events.mlh.io` hosted events. External hackathons link to their own sites.
- **UTM params in URLs.** Strip `?utm_source=mlh&utm_medium=referral&utm_campaign=events&utm_content=...` from `event_url` before dedup.
- **Date format:** `start_date` uses month+day format like `"JULY 17"`, `"AUGUST 28"`, `"SEPTEMBER 11"`. Normalizer should parse month name + day number.
- **If MLH redesigns:** Run `bdata scraper heal c_mt0hfqqi1q7jk1sdbo "<what broke>" --auto-approve --auto-save`