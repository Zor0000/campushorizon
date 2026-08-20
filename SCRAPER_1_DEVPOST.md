# Scraper 1 — Devpost Hackathon Listings

The first Scraper Studio collector built for CampusHorizon. This file documents
the scraper's full lifecycle: what it does, how it was built, what broke,
how it was repaired, and the exact data contract the Django normalizer will
parse.

---

## 1. Overview

| Property | Value |
|---|---|
| Source | Devpost (`devpost.com`) |
| Target URL | `https://devpost.com/hackathons` |
| Collector ID | `c_msz1ehqzhdlpeq7og` |
| Name | `devpost-hackathons` |
| Status | ✅ **Live & verified** (Aug 18, 2026) |
| Architecture | **Single-stage Discovery** — extracts everything from the listing page cards; no navigation to individual hackathon pages |
| Output | Per-page record: `{"hackathons": [...], "product_page_url", "input"}` |
| Extracted data | title, submission deadline, prize amount, tags, online/in-person, URL |
| Why Devpost | Hackathon listings for students; no pre-built Bright Data scraper exists → valid long-tail target |

**What the dashboard gets:** 9 unique hackathons per run, each with a
countdown-able deadline, prize info, tags for AI/ML filtering, and an online/
in-person flag — everything the student lens needs (free, online, deadline < 7 days).

---

## 2. Timeline — the full incident flow

### 2.1 Create (2026-08-18 19:09 UTC)

```bash
npx -p @brightdata/cli bdata scraper create https://devpost.com/hackathons \
  "From the hackathon listing page, extract every hackathon card: title, submission deadline, prize amount, technology tags, whether the event is online or in-person (with city/country), and the link to the hackathon page." \
  --name devpost-hackathons --pretty -o tmp/devpost_create.json
```

**Result:** generation completed in ~216 poll attempts.
`collector_id: c_msz1ehqzhdlpeq7og`, status `done`, view URL
`https://brightdata.com/cp/scrapers/c_msz1ehqzhdlpeq7og`.

**Generated architecture (initial, 2 stages):**

- **Entry (Discovery) stage** — interaction code:
  ```js
  const hackathon_tile_selector = '.hackathon-tile .tile-anchor';
  wait(hackathon_tile_selector);
  const {urls} = parse();
  for (let hackathon_url of urls) { next_stage({url: hackathon_url}); }
  // pagination: rerun_stage for pages 2..10
  ```
- **Parser** (stage 1): extracts `href` from `.hackathon-tile .tile-anchor`.
- **PDP (detail) stage**: visits each hackathon URL, extracts fields.

### 2.2 First run → `[]` (INCIDENT #1)

```bash
npx -p @brightdata/cli bdata scraper run c_msz1ehqzhdlpeq7og https://devpost.com/hackathons --pretty -o tmp/devpost_sample.json
```

- Realtime mode hit the page limit → switched to batch mode.
- Batch job completed fast with **zero records** (`[]`).

### 2.3 Diagnosis (client-side rendering — ROOT CAUSE #1)

Manually fetched `https://devpost.com/hackathons` and inspected the HTML:

- **Zero hackathon cards in server HTML** — no `.hackathon-tile`, no
  `/hackathons/<slug>` links. The page is a client-side-rendered shell
  (`id="hackathon-search"`); listings load via JavaScript.
- The RSS fallback (`/hackathons.rss`) returns `403` to plain bots — proving
  why browser rendering + unblocking infrastructure is needed.
- `.hackathon-tile .tile-anchor` is **stale Devpost markup** — the selector the
  AI generated no longer matches the rendered DOM.

**Conclusion:** discovery found 0 URLs → `next_stage()` never fired → batch
delivered `[]`. Zero rows = discovery problem (not the detail stage).

### 2.4 Heal #1 — parser fixed, but nothing persisted

```bash
npx -p @brightdata/cli bdata scraper heal c_msz1ehqzhdlpeq7og \
  "The discovery stage returns zero hackathon URLs ... .hackathon-tile .tile-anchor no longer matches the current Devpost markup. Identify the current hackathon listing card structure in the rendered DOM and extract the href of every hackathon card link."
```

- **Preview passed** — 9 hackathons with full fields (title, deadline, prize,
  tags, location).
- `bdata scraper approve c_msz1ehqzhdlpeq7og` → status `done`.
- **Re-run still returned `[]`.** (INCIDENT #2 — see root cause #2.)

### 2.5 Single-URL debugging → the smoking gun

Running the collector on a single hackathon URL exposed the real error:

```json
{"error": "Crawler error: waiting for selector \".hackathon-tile .tile-anchor\" failed: timeout 30000ms exceeded",
 "error_code": "wait_element_timeout"}
```

- **Batch mode silently drops erroring items** (`[]`); single-URL runs expose
  `error_code`. (ROOT CAUSE #2, part A.)

### 2.6 Heal #2 — demand single-stage extraction

```bash
bdata scraper heal c_msz1ehqzhdlpeq7og \
  "Running the collector still fails after the previous heal. The ENTRY stage interaction code calls wait('.hackathon-tile .tile-anchor') ... Fix the entry stage: navigate to the listing page, wait for the CURRENT hackathon card element ... extract one record per hackathon card directly from the listing page ... Do not navigate to individual hackathon pages."
```

- Preview: 1 step (down from 2), records with full fields. **Approve → re-run
  still `[]`.** (ROOT CAUSE #2, part B.)

### 2.7 Root cause #2 found: approval ≠ persistence

**Plain `bdata scraper approve` does not persist the healed code.** Previews
always show the *candidate* code; runs use the *saved* template — so all runs
kept using the original broken template.

### 2.8 Heal #3 — the fix that stuck

```bash
bdata scraper heal c_msz1ehqzhdlpeq7og \
  "The ENTRY stage interaction code calls wait('.hackathon-tile .tile-anchor') ... Single stage, no navigation to individual hackathon pages." \
  --auto-approve --auto-save
```

- `status: done`, template persisted.
- **Re-run → 10 records, 9 unique hackathons, all fields populated. ✅**

### 2.9 Final verification

| Check | Result |
|---|---|
| Records | 10 page-records × 9 hackathons (page 1) |
| Unique hackathons | 9 (dedupe by `hackathon_url` in the pipeline) |
| Titles | RevenueCat Shipaton 2026, Agentic Cinema, All Things Agentic, ... |
| Deadlines | `"Jul 31 - Oct 01, 2026"` format |
| Prizes | `{"value": 685000, "currency": "USD", "symbol": "$"}` |
| Location | `"Online"` / city strings |
| Tags | arrays like `["Design","Gaming","Mobile"]` |

---

## 3. Issues & solutions summary

| # | Issue | Root cause | Solution |
|---|---|---|---|
| 1 | Run returns `[]` | Client-side-rendered listing; AI used stale selector `.hackathon-tile .tile-anchor` | Diagnose by fetching raw HTML + inspecting rendered DOM; heal with explicit "current card structure" prompt |
| 2a | `[]` hides the failure | Batch mode drops erroring records silently | Debug via single-URL run → read `error_code` (`wait_element_timeout`, `dead_page`) |
| 2b | Heals "worked" but runs didn't | `approve` alone doesn't persist the template | Use `heal --auto-approve --auto-save` so the fixed code is saved |
| 3 | 9 hackathons ×10 pages | Template paginates `max_pages=10` but the listing is one page | Normalizer dedupes by `hackathon_url` (stretch: heal pagination away) |
| 4 | Nested output shape | Discovery returns per-page wrapper `{hackathons: [...]}` | Normalizer unwraps the `hackathons` array |

---

## 4. Example input & output

### 4.1 Inputs

**Create description:** "From the hackathon listing page, extract every
hackathon card: title, submission deadline, prize amount, technology tags,
whether the event is online or in-person (with city/country), and the link to
the hackathon page."

**Heal prompt (final, successful):** see §2.8. Pattern: name the broken
selector, name the error (`wait_element_timeout`), state where the data lives
(rendered DOM cards), demand single-stage extraction.

**Run command:**

```bash
npx -p @brightdata/cli bdata scraper run c_msz1ehqzhdlpeq7og https://devpost.com/hackathons --pretty -o tmp/devpost_sample.json
```

### 4.2 Output (real sample, 2026-08-18)

One hackathon record (inside the `hackathons` array):

```json
{
  "title": "RevenueCat Shipaton 2026",
  "submission_deadline": "Jul 31 - Oct 01, 2026",
  "prize_amount": {
    "value": 685000,
    "currency": "USD",
    "symbol": "$"
  },
  "tags": ["Design", "Gaming", "Mobile"],
  "location_type": "Online",
  "status": "about 1 month left",
  "hackathon_url": "https://revenuecat-shipaton-2026.devpost.com/?ref_feature=challenge&ref_medium=discover"
}
```

Record wrapper (one per page):

```json
{
  "hackathons": [ ...9 hackathon objects... ],
  "product_page_url": "https://devpost.com/hackathons",
  "input": { "url": "https://devpost.com/hackathons" }
}
```

Full sample: `tmp/devpost_sample.json`.

---

## 5. Data contract for the normalizer

| Scraper field | Type | Normalized `Event` field | Notes |
|---|---|---|---|
| `title` | string | `title` | |
| `submission_deadline` | string `"Jul 31 - Oct 01, 2026"` | `deadline` | parse end date (or start) → ISO |
| `prize_amount.value` | int | `prizes` (display string) | render `$685,000 USD` |
| `prize_amount.currency` | string | | |
| `prize_amount.symbol` | string | | |
| `tags` | string[] | `tags` | |
| `location_type` | string | `is_online` | `"Online"` → True, else city name |
| `hackathon_url` | string | `url` | also the dedup key |
| `status` | string | (optional display) | e.g. `"22 days left"` |

**Normalizer steps:** unwrap `hackathons` per page → drop empty/invalid →
dedupe by `hackathon_url` → map fields → upsert.

---

## 6. Runbook references

- `AGENTS.md` — pinned Collector ID table (§ Pinned Collector IDs)
- `SCRAPER_SETUP.md` — generic per-source process + troubleshooting lessons
- `tmp/devpost_create.json` — create response envelope
- `tmp/devpost_sample.json` — verified run output
- `tmp/devpost_heal.json` / `devpost_heal2.json` / `devpost_heal3.json` — heal envelopes
- `tmp/devpost_approve.json` — approve response
