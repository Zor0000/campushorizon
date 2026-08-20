# Scraper 4 — Devfolio Hackathon Platform

The fourth Scraper Studio collector built for CampusHorizon. This file documents
the scraper's full lifecycle: what it does, how it was built, what broke,
how it was repaired, and the exact data contract the Django normalizer will
parse.

---

## 1. Overview

| Property | Value |
|---|---|
| Source | Devfolio (`devfolio.co`) |
| Target URL | `https://devfolio.co/hackathons` |
| Collector ID | `c_mt0y94lp18i9rcuhhv` |
| Name | `devfolio-hackathons-v2` |
| Status | ✅ **Live & verified** (Aug 20, 2026) |
| Architecture | **Single-stage Discovery** — extracts everything from the listing page cards; no navigation to individual hackathon pages |
| Output | Flat array of hackathon objects |
| Extracted data | hackathon_name, submission_deadline, prize_amount, product_page_url |
| Why Devfolio | Hackathon platform for students; no pre-built Bright Data scraper exists → valid long-tail target |

**What the dashboard gets:** Hackathons with countdown-able deadlines, prize information, and direct event URLs — everything the student lens needs (free, online, deadline < 7 days).

---

## 2. Timeline — the full incident flow

### 2.1 Create v1 (2026-08-20 03:10 UTC) — Wrong URL

```bash
npx -p @brightdata/cli bdata scraper create https://devfolio.co \
  "SINGLE-STAGE extraction from this hackathon platform homepage..." \
  --name devfolio-hackathons --pretty -o tmp/devfolio_create.json
```

**Result:** `collector_id: c_mt0y01c02c02v5dei1`, status `done`.

**Problem:** Targeted homepage (`devfolio.co`) instead of hackathons listing page (`devfolio.co/hackathons`). Homepage has no hackathon cards → empty extraction.

### 2.2 First run v1 → Failed

```bash
npx -p @brightdata/cli bdata scraper run c_mt0y01c02c02v5dei1 https://devfolio.co --pretty
```

- 43 records extracted, **0 hackathons** (empty arrays)
- Discovered subdomains (venture-26.devfolio.co, hackinverse-s1.devfolio.co) but no data
- Root cause: wrong target URL

### 2.3 Create v2 (2026-08-20 03:17 UTC) — Correct URL

```bash
npx -p @brightdata/cli bdata scraper create https://devfolio.co/hackathons \
  "SINGLE-STAGE extraction from this hackathon listing page. Wait for hackathon cards to fully render. From each visible hackathon card, extract: hackathon_name, submission_deadline, prize_amount, whether the event is online or offline, and the link to the hackathon page. Do NOT navigate to detail pages. Return one record per hackathon card." \
  --name devfolio-hackathons-v2 --pretty -o tmp/devfolio_v2_create.json
```

**Result:** `collector_id: c_mt0y94lp18i9rcuhhv`, status `done`, 291 poll attempts.

### 2.4 First run v2 → Success

```bash
npx -p @brightdata/cli bdata scraper run c_mt0y94lp18i9rcuhhv https://devfolio.co/hackathons --pretty -o tmp/devfolio_v2_sample.json
```

- **28 hackathons** extracted with names, deadlines, and prizes.
- Single-stage design worked on first generation.

---

## 3. Issues & solutions summary

| # | Issue | Root cause | Solution |
|---|---|---|---|
| 1 | v1 returned 0 hackathons | Wrong target URL (`devfolio.co` homepage) | Created v2 with correct URL (`devfolio.co/hackathons`) |

---

## 4. Example input & output

### 4.1 Inputs

**Create description:** "SINGLE-STAGE extraction from this hackathon listing page. Wait for hackathon cards to fully render. From each visible hackathon card, extract: hackathon_name, submission_deadline, prize_amount, whether the event is online or offline, and the link to the hackathon page. Do NOT navigate to detail pages. Return one record per hackathon card."

**Run command:**

```bash
npx -p @brightdata/cli bdata scraper run c_mt0y94lp18i9rcuhhv https://devfolio.co/hackathons --pretty -o tmp/devfolio_v2_sample.json
```

### 4.2 Output (real sample, 2026-08-20)

Flat array of hackathon objects:

```json
{
  "hackathon_name": "The Great Agent Hackathon",
  "submission_deadline": "Sep 25 - 26, 2026",
  "prize_amount": {
    "value": 15318,
    "currency": "USD",
    "symbol": "$"
  },
  "product_page_url": "https://the-great-agent-hackathon.devfolio.co/"
}
```

All 28 hackathons from latest run:

| # | Name | Deadline | Prize |
|---|---|---|---|
| 1 | Hefty-Hacks | — | — |
| 2 | Convergence | Oct 31 - Nov 1, 2026 | — |
| 3 | DOMINION 2026 | Sep 2 - 3, 2026 | — |
| 4 | MUBA Blockchain Hackathon | Aug 26 - Sep 6, 2026 | — |
| 5 | Road to Devcon - NITK Surathkal | Aug 17 - 23, 2026 | $300 |
| 6 | Dora Hack 2.0 | Aug 20 - 30, 2026 | $213,550 |
| 7 | The Great Agent Hackathon | Sep 25 - 26, 2026 | $15,318 |
| 8 | VENTURE'26 | Sep 10 - 11, 2026 | — |
| 9 | Metamorph 2.0 | Sep 12 - 13, 2026 | $1,100 |
| 10 | ETHKochi | Sep 5 - 6, 2026 | — |
| 11 | HackInverse 1.0 | Sep 12 - 13, 2026 | — |
| 12 | Recursion Edition II | Sep 3 - 4, 2026 | $5,000 |
| 13 | CodeWars1.0 | Aug 22 - 23, 2026 | $524 |
| 14 | RevengersHack | Aug 22 - 23, 2026 | $30,000 |
| 15 | Road To Devcon | — | — |
| 16 | Hackify 3.0 | Oct 9 - 11, 2026 | — |
| 17 | FusioniX2026 | Sep 11 - 12, 2026 | $524 |
| 18 | HackVerse: Into the Web | Sep 1 - 2, 2026 | $3,100 |
| 19 | Innohacks 4.0 | Oct 3 - 4, 2026 | — |
| 20 | HackSpire'26 | Oct 2 - 3, 2026 | $800 |
| 21 | HackNex Season 2 | Sep 25 - 26, 2026 | $289 |
| 22 | Buildora Hackathon | Aug 8, 2026 | — |
| 23 | WebCraft24 | Sep 25 - 26, 2026 | $500 |
| 24 | Infinity Hacks 2026 | Aug 15 - 16, 2026 | — |
| 25 | Push to Prod Hackathon | Aug 8, 2026 | $11,000 |
| 26 | HackTopus'FE | Oct 14 - 16, 2026 | $845 |
| 27 | Binary Hacks 4.0 | Sep 21 - 22, 2026 | — |
| 28 | CodeStorm 2026: FutureForge | — | — |

Full sample: `tmp/devfolio_v2_sample.json`.

---

## 5. Data contract for the normalizer

| Scraper field | Type | Normalized `Event` field | Notes |
|---|---|---|---|
| `hackathon_name` | string | `title` | |
| `submission_deadline` | string `"Sep 25 - 26, 2026"` | `deadline` | Parse end date → ISO datetime |
| `prize_amount` | object `{value, currency, symbol}` | `prizes` | Render as `"$15,318 USD"` |
| `product_page_url` | string | `url` | also the dedup key |

**Note:** `is_online` field is not extracted from the listing page (all N/A). The normalizer should default to `None` or fetch from detail page if needed.

**Normalizer steps:** iterate flat array → drop empty/invalid → dedupe by `product_page_url` → parse `submission_deadline` to ISO datetime → format `prize_amount` → map fields → upsert.

---

## 6. Runbook references

- `AGENTS.md` — pinned Collector ID table (§ Pinned Collector IDs)
- `SCRAPER_SETUP.md` — generic per-source process + troubleshooting lessons
- `tmp/devfolio_v2_create.json` — create response envelope
- `tmp/devfolio_v2_sample.json` — verified run output (28 hackathons)

---

## 7. Notes for future maintenance

- **Target URL matters.** Must be `https://devfolio.co/hackathons`, NOT the homepage.
- **Prize format.** `prize_amount` is an object with `value` (int), `currency` (string), `symbol` (string). Normalizer should render as `"$15,318 USD"`.
- **Date format.** `submission_deadline` uses format like `"Sep 25 - 26, 2026"` or `"Aug 8, 2026"`. Parse the end date.
- **If Devfolio redesigns:** Run `bdata scraper heal c_mt0y94lp18i9rcuhhv "<what broke>" --auto-approve --auto-save`