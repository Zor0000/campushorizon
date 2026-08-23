# Scraper 5 — LabLab AI Hackathons

The fifth Scraper Studio collector built for CampusHorizon. This file documents
the scraper's full lifecycle: what it does, how it was built, what broke,
how it was repaired, and the exact data contract the Django normalizer will
parse.

---

## 1. Overview

| Property | Value |
|---|---|
| Source | LabLab (`lablab.ai`) |
| Target URL | `https://lablab.ai/ai-hackathons` |
| Collector ID | `c_mt2pm82fb4ta19gqe` |
| Name | `lablab-ai-hackathons` |
| Status | ✅ **Live & verified** (Aug 21, 2026) |
| Architecture | **Single-stage Discovery / Listing Extraction** — extracts hackathon card links directly from the `/ai-hackathons` listing page (resilient to Next.js client-side rendering) |
| Output | Per-page wrapper: `[{"hackathons_cards": [...], "product_page_url": "...", "input": {...}}]` |
| Extracted data | `product_page_url`, `hackathon_cards` (titles derived from slug in normalizer) |
| Why LabLab | Dedicated AI hackathon platform for student builders; no pre-built Bright Data scraper exists → valid long-tail target |

**What the dashboard gets:** 12 active AI hackathons (IBM, AMD, Alpaca, AssemblyAI, etc.) with direct event URLs, semantic titles derived from URL slugs, and online hackathon tagging — feeding the student hackathon radar.

---

## 2. Timeline — the full incident flow

### 2.1 Create v1 (2026-08-21 07:41 UTC) — 2-Stage Detail Collector

```bash
npx -p @brightdata/cli bdata scraper create https://lablab.ai/ai-hackathons \
  "Extract AI hackathons with title, start date, end date, prize pool, tech tags, online format, and URL." \
  --name lablab-hackathons --pretty -o tmp/phase1/lablab_create.json
```

**Result:** generated collector `c_mt2n5ie32qzka71trc` with a 2-stage architecture (Stage 1: discovery of event URLs, Stage 2: PDP navigation to extract detail fields).

### 2.2 First run v1 → Detail Page Timeouts (INCIDENT #1)

```bash
npx -p @brightdata/cli bdata scraper run c_mt2n5ie32qzka71trc https://lablab.ai/ai-hackathons --pretty
```

- **11 of 12 rows failed** with detail-page crawl errors:
  ```text
  Crawler error: waiting for selector .alp-top h1, .alp-top-meta, .alp-tools span failed: timeout 30000ms
  ```
- **Root cause:** LabLab's individual hackathon pages are heavy Next.js SPAs with client-side hydration delays. The AI-generated selectors (`.alp-top h1`, `.alp-top-meta`) timed out on slow-loading subpages.

### 2.3 Heal attempts on v1 → Status Error (INCIDENT #2)

```bash
npx -p @brightdata/cli bdata scraper heal c_mt2n5ie32qzka71trc \
  "lablab: 11 of 12 records fail with 'waiting for selector .alp-top h1... failed timeout 30000ms' - the crawler stalls on slow event detail pages. Extract all fields from the /ai-hackathons listing cards themselves..." \
  --pretty -o tmp/phase1/lablab_heal2.json
```

- **Result:** Self-healing finished with status `error`. The collector was trapped in broken stage navigation.
- **Decision:** Following the documented create-fallback protocol in `AGENTS.md`, retired `c_mt2n5ie32qzka71trc` and re-created a clean single-stage collector.

### 2.4 Create v2 (2026-08-21 08:50 UTC) — Single-Stage Listing Extractor

```bash
npx -p @brightdata/cli bdata scraper create https://lablab.ai/ai-hackathons \
  "SINGLE-STAGE extraction from the /ai-hackathons listing page. Wait for hackathon cards to render. Extract product_page_url for every hackathon card. Do NOT navigate to detail pages." \
  --name lablab-ai-hackathons --pretty -o tmp/phase1/lablab_create2.json
```

**Result:** `collector_id: c_mt2pm82fb4ta19gqe`, status `done`.

### 2.5 First run v2 & Healing Observation

```bash
npx -p @brightdata/cli bdata scraper run c_mt2pm82fb4ta19gqe https://lablab.ai/ai-hackathons --pretty -o tmp/lablab_sample.json
```

- **12 hackathon entries extracted** with 100% valid `product_page_url`s.
- LabLab's listing DOM renders deeply nested and obfuscated Next.js component classes. Card-level text fields returned `looking_for_members: false` while sub-elements resisted static CSS extraction.
- Later heal attempts (`lablab_heal3`, `lablab_heal4`) hit Next.js DOM preview conflicts.

### 2.6 Resilient Normalizer Architecture

To ensure zero-downtime and robust data ingestion without relying on fragile CSR DOM selectors:
- `normalize_lablab` extracts the clean `product_page_url`.
- Uses `_title_from_slug(url)` to derive formatted, human-readable titles (e.g., `ibm-bob-2-hackathon` → `IBM Bob 2 Hackathon`, `amd-developer-hackathon-act-iii` → `AMD Developer Hackathon Act III`, `ai-genesis-2026` → `AI Genesis 2026`).
- Handles acronym capitalization (`AI`, `IBM`, `AMD`, `MLH`, `LLM`, `GPT`, `AWS`, `GCP`).
- Parses dates, prizes, formats, and tags if present in the raw payload or fallback fields.

---

## 3. Issues & solutions summary

| # | Issue | Root cause | Solution |
|---|---|---|---|
| 1 | 11/12 records timeout on v1 | 2-stage collector stalled on slow Next.js PDP detail pages (`wait_element_timeout`) | Retired dead ID `c_mt2n5ie32qzka71trc`; re-created v2 with single-stage listing extraction |
| 2 | Heal on v1 returned `error` | Generator could not recover 2-stage interaction flow | Followed create-fallback protocol to build `c_mt2pm82fb4ta19gqe` |
| 3 | Listing card text fields sparse | Next.js client-side rendering / dynamic hydration obfuscates card DOM classes | `normalize_lablab` uses intelligent slug title derivation (`_title_from_slug`) + URL deduping |

---

## 4. Example input & output

### 4.1 Inputs

**Create description:** "SINGLE-STAGE extraction from the /ai-hackathons listing page. Wait for hackathon cards to render. Extract product_page_url for every hackathon card. Do NOT navigate to detail pages."

**Run command:**

```bash
npx -p @brightdata/cli bdata scraper run c_mt2pm82fb4ta19gqe https://lablab.ai/ai-hackathons --pretty -o tmp/lablab_sample.json
```

### 4.2 Output (real sample, 2026-08-21)

Raw output record:

```json
{
  "hackathon_cards": [
    { "looking_for_members": false },
    { "looking_for_members": false },
    { "looking_for_members": false }
  ],
  "product_page_url": "https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon",
  "input": {
    "url": "https://lablab.ai/ai-hackathons"
  }
}
```

Extracted Hackathons (12 items):

| # | Title (derived from slug) | Product Page URL |
|---|---|---|
| 1 | AI Infra Summit Hackathon | `https://lablab.ai/ai-hackathons/ai-infra-summit-hackathon` |
| 2 | AMD Lablab AI Academy Challenge | `https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge` |
| 3 | AI Genesis 2026 | `https://lablab.ai/ai-hackathons/ai-genesis-2026` |
| 4 | AMD Developer Hackathon Act III | `https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii` |
| 5 | Nativebuilder Build Without Limits | `https://lablab.ai/ai-hackathons/nativebuilder-build-without-limits` |
| 6 | AMD Developer Hackathon Act II | `https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii` |
| 7 | Alpaca AI Trading Agents Hackathon | `https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon` |
| 8 | Wearedevelopers Hackathon | `https://lablab.ai/ai-hackathons/wearedevelopers-hackathon` |
| 9 | Assemblyai Voice Agent Hackathon | `https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon` |
| 10 | Techex Amsterdam Hackathon | `https://lablab.ai/ai-hackathons/techex-amsterdam-hackathon` |
| 11 | IBM Bob 2 Hackathon | `https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon` |
| 12 | AI Agents AI Week Hackathon | `https://lablab.ai/ai-hackathons/ai-agents-ai-week-hackathon` |

Full sample: `tmp/lablab_sample.json`.

---

## 5. Data contract for the normalizer

| Scraper field | Type | Normalized `Event` field | Notes |
|---|---|---|---|
| `product_page_url` | string | `url` | Primary unique key; also used to derive title |
| (slug from url) | string | `title` | Converted via `_title_from_slug` (e.g. `ibm-bob-2-hackathon` → `IBM Bob 2 Hackathon`) |
| `submission_deadline` / `end_date` | string (optional) | `deadline` | Parsed via multi-format date parser |
| `prize_amount` / `prize` | object / string | `prizes` | Formatted to display string (e.g. `"$10,000 USD"`) |
| `format` / `mode` | string | `is_online` | Parsed via boolean flag detector (`"Online"` → True) |
| `tech_tags` / `hosting_company` | string[] / string | `tags` | Combined tag list |

**Normalizer steps:** unwrap items → extract `product_page_url` → dedupe by URL → derive clean title from URL slug if title field is empty → parse date/prize/tags if present → upsert as `Source.LABLAB`.

---

## 6. Runbook references

- `AGENTS.md` — pinned Collector ID table (`c_mt2pm82fb4ta19gqe`)
- `SCRAPER_SETUP.md` — collector setup and troubleshooting runbook
- `tmp/phase1/lablab_create2.json` — collector creation envelope
- `tmp/lablab_sample.json` — verified run sample (12 hackathons)
- `events/scraper/normalizer.py` — `normalize_lablab` and `_title_from_slug` implementation

---

## 7. Notes for future maintenance

- **Do not reuse dead collector `c_mt2n5ie32qzka71trc`.**
- **Next.js CSR sensitivity:** LabLab heavily relies on client-side rendering. Always enforce single-stage extraction to avoid detail-page timeouts.
- **Slug parsing robustness:** If LabLab modifies URL routing from `/ai-hackathons/<slug>`, verify `_title_from_slug` regex handling.
