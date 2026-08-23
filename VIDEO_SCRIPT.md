# CampusHorizon — Video Presentation & Demo Script
**Hackathon:** Bright Data Scrape-Verse Hackathon  
**Target Video Length:** ~3 Minutes (180–200 seconds)  
**Primary Focus:** Self-Healing Web Scraping via Bright Data CLI & Scraper Studio, Student Hackathon Radar, Zero-Downtime Pipeline.

---

## 🎬 Video Production Overview

| Parameter | Recommended Setting |
|---|---|
| **Resolution** | 1080p (1920x1080) or 4K (3840x2160) at 60fps |
| **Theme / Aesthetic** | Dark mode (VS Code / Terminal / Browser) for seamless transition with CampusHorizon UI |
| **Voiceover Tone** | Energetic, crisp, developer-focused, confident, professional |
| **Pacing** | ~130-140 words per minute |

---

## 📋 Pre-Recording Setup Checklist

1. **Terminal Setup:**
   - Font size enlarged (16–18pt) for clean readability.
   - Terminal window 1 (Django Server): `source .venv/bin/activate && python manage.py runserver`
   - Terminal window 2 (Commands / Demo): ready for `bdata` and `python manage.py` commands.
2. **Browser Setup (Clean Profile):**
   - Tab 1: `http://localhost:8000/` (CampusHorizon Landing Page)
   - Tab 2: `http://localhost:8000/hackathons/` (Hackathons Feed)
   - Tab 3: `http://localhost:8000/tech-events/` (Tech Events Feed)
   - Tab 4: GitHub Repository (`.github/workflows/collect.yml` and Actions tab)
   - Tab 5: Bright Data Dashboard / Collector Page
3. **Audio / Mic Check:**
   - Clean audio, background noise suppressed, pop filter enabled.

---

## ⏱️ Scene-by-Scene Storyboard & Script

---

### SCENE 1: The Problem & Hook (0:00 – 0:30)
**Duration:** 30 seconds  
**Visuals:**
- Start with rapid browser clips showing student platforms: Devpost, MLH, Devfolio, Luma, Meetup.
- Show a mock browser console / terminal throwing `404 Not Found`, `wait_element_timeout`, or broken HTML scrapers.
- Quick cut to a slide or title card: **"CampusHorizon: Self-Healing Event Radar"**.

**Action on Screen:**
- Switch between 3 different hackathon websites to illustrate fragmentation.

**Voiceover / Speech:**
> *"Every student developer knows the feeling: you find out about an incredible hackathon with \$50,000 in prizes… three days after the deadline closed.*
> 
> *Opportunities are scattered across Devpost, MLH, Devfolio, LabLab, Luma, and Meetup. But building a centralized scraper for these platforms is a nightmare — SPAs, dynamic client-side rendering, and frequent website redesigns break traditional scrapers instantly.*
> 
> *Enter **CampusHorizon** — an intelligent, student-first event discovery radar powered by self-healing Bright Data scrapers."*

---

### SCENE 2: The Solution & Unified Radar (0:30 – 1:00)
**Duration:** 30 seconds  
**Visuals:**
- Screen capture of the CampusHorizon landing page (`http://localhost:8000/`).
- Smooth mouse hover over key metrics: **"300+ Events Tracked"**, **"6 Sources"**, **"Ending This Week"**.
- Click search bar, type `AI`, and hit Search.

**Action on Screen:**
- Scroll down the Landing page hero section.
- Show the quick breakdown of "Ending this week" cards with countdown badges.

**Voiceover / Speech:**
> *"CampusHorizon aggregates over 300 hackathons and tech events into one unified dashboard with zero noise.*
> 
> *It's designed specifically through a student lens: instant countdown timers, online-only flags, prize pool breakdowns, and tech stack tags.*
> 
> *Whether you're looking for global virtual hackathons or in-person developer meetups nearby, everything is indexed and standardized into a single schema."*

---

### SCENE 3: The Hero Demo — Self-Healing Web Scraping (1:00 – 2:05)
**Duration:** 65 seconds ⭐ *(Most important section for judges)*  
**Visuals:**
- Split-screen or full terminal view.
- Show Bright Data CLI commands and Django self-healing management commands in action.

**Action & Commands on Screen:**

1. **Show Collector Architecture:**
   ```bash
   npx -p @brightdata/cli bdata scraper run c_msz1ehqzhdlpeq7og https://devpost.com/hackathons --pretty
   ```
2. **Explain the Incident & Detection:**
   Show the output of `heal_check`:
   ```bash
   python manage.py heal_check
   ```
   *(Show the console output detecting Rule R0 / R1: 0 records extracted due to layout change).*
3. **Trigger AI Self-Healing:**
   ```bash
   python manage.py heal_check --auto-heal
   ```
   *or CLI:*
   ```bash
   npx -p @brightdata/cli bdata scraper heal c_msz1ehqzhdlpeq7og "Current hackathon card selector in rendered DOM" --auto-approve --auto-save
   ```
4. **Instant Recovery with Zero Downstream Code Changes:**
   ```bash
   python manage.py collect_events --online --source devpost
   ```

**Voiceover / Speech:**
> *"Now, here is where Bright Data Scraper Studio transforms the entire pipeline.*
> 
> *All our scrapers target long-tail sites without pre-built scrapers. When Devpost migrated to client-side rendering with empty initial server HTML, traditional scrapers would die permanently.*
> 
> *With CampusHorizon, our built-in health validator continuously enforces data integrity rules. When empty payloads or dropped selectors are detected, `heal_check --auto-heal` triggers Bright Data's `refactor_template` endpoint.*
> 
> *Bright Data's AI inspects the live rendered DOM, generates new robust selectors, and updates the scraper template. Once approved, we re-run collection — and the pipeline recovers immediately!*
> 
> *Notice what happened: **The Collector ID stayed identical, no database migrations were needed, and not a single line of application code had to change.** That is true self-healing web data."*

---

### SCENE 4: Interactive UI & Category-Aware Feeds (2:05 – 2:40)
**Duration:** 35 seconds  
**Visuals:**
- Switch to browser at `http://localhost:8000/hackathons/`.
- Interactive filtering demo using HTMX:
  - Toggle **"Online only"** checkbox (instant dynamic update).
  - Toggle **"Has prizes"** checkbox.
  - Switch source filters (e.g., filter by Devpost, Devfolio, MLH).
  - Click **"Tech Events"** in navbar (`/tech-events/`) to show Luma & Meetup events with custom start date badges.
  - Click **"Load more events"** pagination.

**Action on Screen:**
- Demonstrate seamless filtering without full page reloads.
- Highlight countdown badges: `"Ends in 2d"`, `"Starts in 5d"`, `"Finished"`.

**Voiceover / Speech:**
> *"On the frontend, CampusHorizon is fast and reactive.*
> 
> *Our Django templates pair with HTMX and Tailwind CSS for instant filtering without full page refreshes. Filter by prize-backed challenges, online-only events, or events ending within seven days.*
> 
> *The UI is category-aware: hackathons display prize pools and deadlines, while tech events from Luma and Meetup cleanly highlight start dates and local venues.*
> 
> *Every event snapshot is tracked over time, allowing us to capture deadline extensions and prize updates automatically."*

---

### SCENE 5: Automated CI/CD & Hackathon Compliance (2:40 – 3:10)
**Duration:** 30 seconds  
**Visuals:**
- Show GitHub Actions `.github/workflows/collect.yml` workflow and recent runs.
- Highlight the Job Summary with health reports.
- Show `db.sqlite3` and `raw/` archives committed to repo for instant offline reproducibility.
- Return to CampusHorizon landing page with GitHub link on screen.

**Action on Screen:**
- Scroll through GitHub Actions workflow showing automated cron at 02:00 IST.
- Show terminal running `python manage.py test events` showing all tests passing.

**Voiceover / Speech:**
> *"Under the hood, our GitHub Actions pipeline runs nightly: triggering collectors via API, validating health, archiving raw payloads, and committing the updated database directly back to main.*
> 
> *Judges can clone the repo and run `python manage.py collect_events` to immediately spin up the complete dashboard offline — zero API keys required.*
> 
> *CampusHorizon strictly adheres to ethical scraping guidelines: strictly scraping publicly available data with zero login-walls.*
> 
> *CampusHorizon proves that with Bright Data Scraper Studio, developers can build resilient, production-ready data pipelines that never break. Thank you!"*

---

## 🎙️ Teleprompter / Continuous Voiceover Script

*(Use this continuous transcript for recording your voiceover track in one take)*

```text
Every student developer knows the feeling: you find out about an incredible hackathon with fifty thousand dollars in prizes… three days after the deadline closed.

Opportunities are scattered across Devpost, MLH, Devfolio, LabLab, Luma, and Meetup. But building a centralized scraper for these platforms is a nightmare — SPAs, dynamic client-side rendering, and frequent website redesigns break traditional scrapers constantly.

Enter CampusHorizon — an intelligent, student-first event discovery radar powered by self-healing Bright Data scrapers.

CampusHorizon aggregates over 300 hackathons and tech events into one unified dashboard with zero noise. It's designed specifically through a student lens: instant countdown timers, online-only flags, prize pool breakdowns, and tech stack tags. Whether you're looking for global virtual hackathons or in-person developer meetups nearby, everything is indexed and standardized into a single schema.

Now, here is where Bright Data Scraper Studio transforms the entire pipeline. All our scrapers target long-tail sites without pre-built scrapers. When Devpost migrated to client-side rendering with empty initial server HTML, traditional scrapers would die permanently.

With CampusHorizon, our built-in health validator continuously enforces data integrity rules. When empty payloads or dropped selectors are detected, heal_check with auto-heal triggers Bright Data's refactor_template endpoint. Bright Data's AI inspects the live rendered DOM, generates new robust selectors, and updates the scraper template. Once approved, we re-run collection — and the pipeline recovers immediately!

Notice what happened: The Collector ID stayed identical, no database migrations were needed, and not a single line of application code had to change. That is true self-healing web data.

On the frontend, CampusHorizon is fast and reactive. Our Django templates pair with HTMX and Tailwind CSS for instant filtering without full page refreshes. Filter by prize-backed challenges, online-only events, or events ending within seven days. The UI is category-aware: hackathons display prize pools and deadlines, while tech events from Luma and Meetup cleanly highlight start dates and local venues.

Under the hood, our GitHub Actions pipeline runs nightly: triggering collectors via API, validating health, archiving raw payloads, and committing the updated database directly back to main. Judges can clone the repo and immediately spin up the complete dashboard offline — zero API keys required.

CampusHorizon proves that with Bright Data Scraper Studio, developers can build resilient, production-ready data pipelines that never break. Thank you!
```

---

## 🏆 Hackathon Judging Criteria Alignment

| Criteria | How It's Addressed in Script & Demo |
|---|---|
| **Bright Data Integration** | Uses Scraper Studio collectors, Bright Data CLI (`bdata`), `POST /dca/trigger`, `GET /dca/dataset`, and `POST /dca/collectors/{id}/refactor_template`. |
| **Self-Healing Capabilities** | Hero demo highlights the full incident lifecycle: DOM change → Detection (R0/R1) → `bdata scraper heal` → `approve` → instant recovery under same Collector ID. |
| **Long-Tail Targets** | Targets Devpost, Luma, MLH, Devfolio, LabLab (no pre-built library scrapers) + custom Meetup collector. |
| **Reproducibility** | Full offline mode with committed sample payloads and SQLite DB; automated tests (`python manage.py test events`). |
| **Ethical Scraping** | Public data only, no login walls, no personal data, `.env` kept strictly private. |
| **Real-World Value** | Solves hackathon & tech event discovery for students and developers worldwide. |
