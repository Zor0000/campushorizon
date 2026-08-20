# Scraper Setup Runbook — CampusHorizon

Hands-on checklist for creating the four Bright Data Scraper Studio collectors
by hand. Follow it top to bottom; each section says exactly what command to run,
what output to expect, and what to check manually before moving on.

When all four collectors exist, their `c_*` IDs go into `AGENTS.md` and later
into `events/scraper/config.py`.

---

## 0. Before you start

| Check | How | Expected |
|---|---|---|
| Node + npx installed | `node -v && npx --version` | Node 18+ (npx ships with npm) |
| Bright Data account | https://brightdata.com sign-in | Logged in |
| Promo `wemakedevs` applied | Profile → Billing → promo code | $50 credit shows up |
| Free tier visible | Dashboard → balance | 5,000 credits/month |
| CLI reachable | `npx -p @brightdata/cli bdata --version` | Prints version (v0.3.5) |

No card needed. Costs are tiny: a listing-page scrape is ~1–3 page loads.

---

## 1. Login (interactive, once)

```bash
npx -p @brightdata/cli bdata login
```

**What happens:** your browser opens → OAuth page → you approve → CLI stores a
token locally.

**Manual check:**
- Browser shows a success page ("logged in").
- No error about expired/denied authorization.
- This token lives on your machine only — it is NOT committed anywhere.

---

## 2. Create the four scrapers

Each `create` takes **5–15 minutes** (up to ~25 for the Luma SPA). The CLI
polls and prints progress. Run them one at a time — Bright Data caps concurrent
AI-flow jobs.

Use `--name` so the collector is recognizable in the dashboard, and `-o` to
save the create response (it contains the Collector ID).

### 2.1 Devpost — hackathon listings

```bash
npx -p @brightdata/cli bdata scraper create https://devpost.com/hackathons \
  "From the hackathon listing page, extract every hackathon card: title, submission deadline, prize amount, technology tags, whether the event is online or in-person (with city/country), and the link to the hackathon page." \
  --name devpost-hackathons --pretty -o tmp/devpost_create.json
```

**Expected output envelope** (new CLI shape):

```json
{
  "collector_id": "c_xxxxxxxxxxxxxxxx",
  "name": "devpost-hackathons",
  "status": "completed",
  "...": "..."
}
```

**Manual checks:**
- `collector_id` starts with `c_` — copy it into the table in §4.
- Status is `completed`, not `failed` or `awaiting_*`.
- For later mapping: `tmp/devpost_create.json` is saved.

### 2.2 Luma — tech category events

Target the tech category page for dated tech events:

```bash
npx -p @brightdata/cli bdata scraper create https://luma.com/tech \
  "SINGLE-STAGE extraction from this tech category page. Wait for event cards to fully render (SPA with infinite scroll). From each visible event card, extract: event_title, event_date (e.g., 'Aug 19, 2026'), event_time (e.g., '6:00 PM'), location (Online or city name), event_url. Do NOT navigate to detail pages. Handle infinite scroll to load all events." \
  --name luma-tech-categories --pretty -o tmp/luma_tech_cat_create.json
```

**Manual checks:**
- Generation may take **up to 25 minutes** — normal for SPAs, let it finish.
- Same envelope shape as Devpost; capture `collector_id`.
- Run on `https://luma.com/tech` only — selectors are page-specific.

### 2.3 MLH — student hackathon calendar

```bash
npx -p @brightdata/cli bdata scraper create https://mlh.io/events \
  "SINGLE-STAGE extraction from this hackathon calendar page. Wait for event cards to fully render. From each visible event card, extract: event_name, start_date, end_date, whether the event is online or in-person with the location, and the link to the event page. Do NOT navigate to detail pages. Handle pagination/infinite scroll to load all events." \
  --name mlh-hackathons --pretty -o tmp/mlh_create.json
```

**Manual checks:** same as §2.1.

**Note:** MLH listing pages show limited info (URL + online/in-person). Full event details (name, dates) only available on `events.mlh.io` hosted events. External hackathon sites (hackgt.com, hackthenorth.com) show only URL on the listing page.

### 2.4 Devfolio — hackathon platform

```bash
npx -p @brightdata/cli bdata scraper create https://devfolio.co/hackathons \
  "SINGLE-STAGE extraction from this hackathon listing page. Wait for hackathon cards to fully render. From each visible hackathon card, extract: hackathon_name, submission_deadline, prize_amount, whether the event is online or offline, and the link to the hackathon page. Do NOT navigate to detail pages. Return one record per hackathon card." \
  --name devfolio-hackathons-v2 --pretty -o tmp/devfolio_v2_create.json
```

**Manual checks:** same as §2.1.

**Note:** Target `https://devfolio.co/hackathons` (not the homepage). The homepage has no hackathon cards.

---

## 3. Run and verify each collector

Always inspect the real output before wiring anything downstream. The output
JSON you get here is the shape the Django normalizer will parse, so save every
sample.

```bash
npx -p @brightdata/cli bdata scraper run <COLLECTOR_ID> <TARGET_URL> --pretty -o tmp/<source>_sample.json
```

| Source | URL to run against |
|---|---|
| Devpost | `https://devpost.com/hackathons` |
| Luma | the same URL you used in `create` |
| MLH | `https://mlh.io/events` |
| Devfolio | `https://devfolio.co` |

**What happens:** async by default — CLI polls until the job completes (up to
10 min). Add `--sync` for fast pages (server-side 25–50 s cap) if you prefer.

### Manual QA checklist (per source, before marking it done)

Look at `tmp/<source>_sample.json` and verify:

- [ ] **Records look sane** — each item is one event, not page chrome.
- [ ] **Title present** — no empty/null titles.
- [ ] **Deadline/date present** — Devpost/Devfolio: submission deadline; MLH: start/end; Luma: date+time.
- [ ] **URLs are real** — item URLs point at the platform, no `about:blank` or duplicated listing URL.
- [ ] **Online detection correct** — online events marked online; in-person have a location string.
- [ ] **Reasonable count** — Devpost ~20–40 cards, MLH ~10–20, Luma/Devfolio a handful to dozens. Zero or 1–2 rows on a populated listing page = broken extraction → heal (see §5).
- [ ] **No duplicates** — same event listed twice.
- [ ] **JSON is an array of objects** (or a documented wrapper the normalizer can unwrap).

---

## 4. Record the Collector IDs

| Source | Collector ID (fill in) | Target URL | Status (✓ when verified) |
|---|---|---|---|
| Devpost | `c_msz1ehqzhdlpeq7og` | `https://devpost.com/hackathons` | ✅ **DONE** — 9 unique hackathons, all fields (healed 3×: stale selector → pagination quirks) |
| Luma | `c_mt09dzgd2mai4o8bhu` | `https://luma.com/tech` | ✅ **DONE** — 5 events, all fields with dates |
| MLH | `c_mt0hfqqi1q7jk1sdbo` | `https://mlh.io/events` | ✅ **DONE** — 70 hackathons, 4 with full dates |
| Devfolio | `c_mt0y94lp18i9rcuhhv` | `https://devfolio.co/hackathons` | ✅ **DONE** — 28 hackathons, names+deadlines+prizes |

Then update `AGENTS.md` (table at the top) with the real IDs, and later put
them into `events/scraper/config.py`.

> Rule: once an ID is recorded, **never re-create that scraper**. Reuse it.
> If it breaks, heal it.

---

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `create` stuck >25 min | AI-flow concurrency cap or complex SPA | Wait; retry with `--max-retries` bump; check dashboard shows a running job |
| `create` returns no `collector_id` | Generation failed | Re-run with a sharper description; try the dashboard AI Agent once |
| `run` returns `[]` / null fields | Site layout changed or JS not captured | `bdata scraper heal <ID> "<what broke>"` → `bdata scraper approve <ID>` → re-run |
| Heal preview looks good but runs still fail | **Healed template not persisted** — plain `approve` may not save the new code; runs keep using the old template | Heal again with `--auto-approve --auto-save` (this fixed the Devpost collector after two plain approves failed) |
| Batch returns `[]` but single-URL run shows an `error` record | Batch mode drops erroring items silently; error records expose the real cause | Run on a single URL (or `--sync`) to see `error_code` (e.g. `wait_element_timeout`, `dead_page`) |
| Heal produced bad fix | Vague heal prompt | `bdata scraper approve <ID> --reject`, then heal again with specifics |
| Duplicate events across sources / pages | MLH events also on Devpost; scrapers paginate and repeat | Dedup in the pipeline by URL (fuzzy title+date is a stretch goal) |
| Luma returns nothing | SPA page not covered by the chosen URL | Pick a specific public `lu.ma/<slug>` event page as the target and re-create |

## Lessons from the Devpost collector (verified)

> Full incident walkthrough (create → break → diagnose → heal → recover) with
> real input/output samples: see `SCRAPER_1_DEVPOST.md`.

- **`wait()` selectors must match the *rendered* DOM.** Devpost's listing is client-side
  rendered: the raw HTML has zero hackathon cards, and the AI-generated
  `.hackathon-tile .tile-anchor` was stale markup → `wait_element_timeout` →
  zero records. Verify card structure in a real browser (DevTools) before
  healing.
- **`heal` preview ≠ saved template.** A heal preview can show perfect data while
  runs still return `[]` if the fix wasn't persisted. Use
  `bdata scraper heal <ID> "<prompt>" --auto-approve --auto-save` to guarantee
  the fixed code is saved.
- **Output shape:** Devpost records are per-page:
  `{"hackathons": [...], "product_page_url": "...", "input": {...}}`. The
  normalizer must unwrap the `hackathons` array and dedupe by
  `hackathon_url` (the template paginates ~10 pages repeating the same 9
  cards).
- **Field shape to map:** `title`, `submission_deadline` (string like
  `"Jul 31 - Oct 01, 2026"`), `prize_amount` (`{value, currency, symbol}`),
  `tags` (array), `location_type` (`"Online"`/city), `status`, `hackathon_url`.

---

## 6. Done — what's next

- [ ] All four `run` commands produced verified samples in `tmp/`
- [ ] `AGENTS.md` table filled with real IDs
- [ ] Samples kept — they define the field mapping for the Django normalizer

Next step: I scaffold the Django project and wire `POST /dca/trigger`
(`bdata scraper run --urls` routes there) into `collect_events`.
