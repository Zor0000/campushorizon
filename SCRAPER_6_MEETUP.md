# Scraper 6 — Meetup Tech Category Events

The sixth Scraper Studio collector built for CampusHorizon. This file documents
the scraper's full lifecycle: what it does, how it was built, what broke,
how it was repaired, and the exact data contract the Django normalizer will
parse.

---

## 1. Overview

| Property | Value |
|---|---|
| Source | Meetup (`meetup.com`) |
| Target URL | `https://www.meetup.com/find/?source=EVENTS&categoryId=546` |
| Collector ID | `c_mt2qwd9216p13lefvg` |
| Name | `meetup-tech-events` |
| Status | ✅ **Live & verified** (Aug 21, 2026) |
| Architecture | **Single-stage Discovery** — extracts tech event cards directly from the Meetup find page with category filtering (`categoryId=546`) |
| Output | Array of page wrappers with nested events: `[{"events": [{"title", "start_date_time", "venue", "group_name"}], "product_page_url", "input"}]` |
| Extracted data | `title`, `start_date_time` (ISO with timezone offset), `venue`, `group_name`, `product_page_url` |
| Why Meetup | Developer meetups, community workshops, and user groups for student builders; documented custom collector exception for granular field control |

**What the dashboard gets:** 46+ curated technology events (AI meetups, cloud workshops, open source talks, architecture deep dives) with precise ISO timestamps, venue location, hosting group attribution, and online/in-person status.

---

## 2. Timeline — the full incident flow

### 2.1 Create v1 (2026-08-21 07:46 UTC) — Unscoped Homepage Collector

```bash
npx -p @brightdata/cli bdata scraper create https://www.meetup.com/ \
  "Extract tech events with title, date, venue, online flag, group name, and URL." \
  --name meetup-events --pretty -o tmp/phase1/meetup_create.json
```

**Result:** generated collector `c_mt2nb1or1052fx65zs`.

### 2.2 First run v1 → Multiple Extraction Failures (INCIDENT #1)

```bash
npx -p @brightdata/cli bdata scraper run c_mt2nb1or1052fx65zs https://www.meetup.com/ --pretty
```

Inspecting the output revealed 4 distinct breakage issues:
1. **Missing `start_date` column:** Date strings were buried inside the raw `venue_location` field rather than extracted separately.
2. **Locale drift (`es-ES`):** Proxy exit nodes triggered Spanish localization, yielding non-English strings like `"Las reservas se abren el vie, 14 ago"`.
3. **Duplicated titles:** Text concatenation bugs produced entries like `"Make Friends & Get Together Make Friends & Get Together"`.
4. **Unscoped non-tech events:** Targeting the generic root URL scraped social and non-technical gatherings.

### 2.3 Heal attempts on v1 → Unstable Selectors

Multiple heal attempts on `c_mt2nb1or1052fx65zs` (see `tmp/phase1/meetup_heal.json` and `meetup_heal2.json`) attempted to force English headers and parse the composite fields, but the underlying template structure remained brittle.

### 2.4 Create v2 (2026-08-21 09:26 UTC) — Category-Scoped Collector

Targeted the explicit Technology category endpoint:

```bash
npx -p @brightdata/cli bdata scraper create "https://www.meetup.com/find/?source=EVENTS&categoryId=546" \
  "SINGLE-STAGE extraction from this Meetup tech events page. Wait for event cards to render. Extract: title, start_date_time (ISO format with timezone offset), venue (or 'Online'), group_name, and product_page_url. Do NOT navigate to detail pages." \
  --name meetup-tech-events --pretty -o tmp/phase1/meetup_create2.json
```

**Result:** `collector_id: c_mt2qwd9216p13lefvg`, status `done`.

### 2.5 First run v2 → Empty Events Array (INCIDENT #2)

```bash
npx -p @brightdata/cli bdata scraper run c_mt2qwd9216p13lefvg "https://www.meetup.com/find/?source=EVENTS&categoryId=546" --pretty
```

- Discovered `product_page_url` records but child `events: []` arrays were empty because the listing card sub-selector wasn't triggering parser actions.

### 2.6 Heal #1 on v2 → Prompt & AI Refactor (2026-08-21 09:35 UTC)

```bash
npx -p @brightdata/cli bdata scraper heal c_mt2qwd9216p13lefvg \
  "meetup tech-events collector: every record has an empty 'events' array - the event urls are found but title, start date/time with year, venue or Online marker, and group name are never extracted from each technology event card on the find page. Populate those fields per event" \
  --pretty -o tmp/phase1/meetup_heal3.json
```

- **Preview succeeded** with clean English technology events:
  ```json
  {
    "events": [
      {
        "title": "Open-Source AI in Practice: Building, Evaluating, and Sharing Agentic Tools",
        "start_date_time": "2026-08-21T14:00:00-04:00",
        "venue": "Pennovation Center",
        "group_name": "Coffee & Code Philly"
      }
    ],
    "product_page_url": "https://www.meetup.com/code-coffee-philly/events/315930163/"
  }
  ```

### 2.7 Approval & Verification

```bash
npx -p @brightdata/cli bdata scraper approve c_mt2qwd9216p13lefvg -o tmp/phase1/meetup_approve3.json
npx -p @brightdata/cli bdata scraper run c_mt2qwd9216p13lefvg "https://www.meetup.com/find/?source=EVENTS&categoryId=546" --pretty -o tmp/meetup_sample.json
```

- **46 tech events extracted** across major developer hubs (Bengaluru, Pune, Hyderabad, Chennai, Mumbai, Delhi, Kolkata).
- ISO timestamps with full timezone offsets (`2026-08-29T17:30:00+05:30`).
- Accurate venue / Online classification and group attribution. ✅

---

## 3. Issues & solutions summary

| # | Issue | Root cause | Solution |
|---|---|---|---|
| 1 | Spanish locale text & missing dates on v1 | Generic root URL target + proxy locale drift | Created v2 targeting explicit tech category `categoryId=546` |
| 2 | Empty `events: []` array on v2 initial run | Interaction script did not bind card children to parser step | Healed with explicit prompt targeting find page tech cards (`meetup_heal3.json`) |
| 3 | Group name attribution in title | Event cards display group separately from event title | Normalizer formats title as `"{title} · {group_name}"` for clarity |

---

## 4. Example input & output

### 4.1 Inputs

**Create description:** "SINGLE-STAGE extraction from this Meetup tech events page. Wait for event cards to render. Extract: title, start_date_time (ISO format with timezone offset), venue (or 'Online'), group_name, and product_page_url. Do NOT navigate to detail pages."

**Heal prompt:** "meetup tech-events collector: every record has an empty 'events' array - the event urls are found but title, start date/time with year, venue or Online marker, and group name are never extracted from each technology event card on the find page. Populate those fields per event"

**Run command:**

```bash
npx -p @brightdata/cli bdata scraper run c_mt2qwd9216p13lefvg "https://www.meetup.com/find/?source=EVENTS&categoryId=546" --pretty -o tmp/meetup_sample.json
```

### 4.2 Output (real sample, 2026-08-21)

Raw output record:

```json
{
  "events": [
    {
      "title": "AI First Engineering: Ship with Coding Agents",
      "start_date_time": "2026-08-29T16:00:00+05:30",
      "venue": "Online",
      "group_name": "Agentic Engineering and Modern Deployments"
    }
  ],
  "product_page_url": "https://www.meetup.com/agentic-engineering-and-modern-deployments/events/315930163/",
  "input": {
    "url": "https://www.meetup.com/find/?location=in--Kolkata&source=EVENTS&categoryId=546"
  }
}
```

Sample of Extracted Events (46 total):

| # | Title | Date / Time | Venue | Group |
|---|---|---|---|---|
| 1 | AI First Engineering: Ship with Coding Agents | 2026-08-29 16:00 IST | Online | Agentic Engineering |
| 2 | Building AI Agents with Microsoft Foundry and MCP | 2026-08-28 10:30 IST | Online | Microsoft Reactor Bengaluru |
| 3 | The Platform Habba: Bengaluru Tech Week 2026 | 2026-09-05 10:30 IST | Freshworks Bengaluru | Platform & Resilience Engineering |
| 4 | Grafana & Friends x Kubernetes Pune Happy Hours | 2026-09-05 10:00 IST | InfraCloud Pune | Grafana & Friends Pune |
| 5 | Building Open Source AI: Intro to Goose & GDK | 2026-08-22 11:00 IST | South Delhi | Bitshala x AAIF |
| 6 | Kube x Agentic AI | 2026-08-22 09:30 IST | Microsoft India Delhi | Grafana & Friends Delhi |

Full sample: `tmp/meetup_sample.json`.

---

## 5. Data contract for the normalizer

| Scraper field | Type | Normalized `Event` field | Notes |
|---|---|---|---|
| `events[].title` | string | `title` | Formatted with group name: `"{title} · {group_name}"` |
| `events[].start_date_time` | ISO datetime string | `deadline` | Parsed to UTC `datetime` object |
| `events[].venue` | string | `location` / `is_online` | `"Online"` → `is_online=True`, `location=""`; else location string |
| `events[].group_name` | string | (title suffix) | Appended to title if not already present |
| `product_page_url` / `event_url` | string | `url` | Primary unique key (query params stripped) |

**Normalizer steps:** unwrap nested `events` arrays from page records → extract event URL → dedupe by URL → parse ISO start datetime → format title with group name suffix → classify online/venue → upsert as `Source.MEETUP`.

---

## 6. Runbook references

- `AGENTS.md` — pinned Collector ID table (`c_mt2qwd9216p13lefvg`)
- `SCRAPER_SETUP.md` — collector setup and troubleshooting runbook
- `tmp/phase1/meetup_create2.json` — collector creation envelope
- `tmp/phase1/meetup_heal3.json` — AI healing envelope
- `tmp/phase1/meetup_approve3.json` — approval envelope
- `tmp/meetup_sample.json` — verified run sample (46 tech events)
- `events/scraper/normalizer.py` — `normalize_meetup` implementation

---

## 7. Notes for future maintenance

- **Documented Exception:** Meetup has a pre-built Bright Data scraper in the library, but CampusHorizon deliberately maintains this custom collector for fine-grained field control (`title`, `start_date_time` with timezone, `venue`, `online`, `group_name`, `url`).
- **Category Filter:** Always include `categoryId=546` in the target URL to ensure event results are restricted to Technology & Engineering.
- **If Meetup redesigns:** Run `bdata scraper heal c_mt2qwd9216p13lefvg "<what broke>" --auto-approve --auto-save`.
