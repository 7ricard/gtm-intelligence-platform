# GTM Intelligence Platform

An AI-powered platform that researches and scores target accounts, turning a company name and domain into a structured go-to-market brief in seconds.

---

## Overview

GTM Intelligence Platform automates the manual research that goes into outbound prospecting. Give it a company name and domain, and it:

1. Scrapes the company homepage, about page, and pricing page.
2. Sends the cleaned text to the Claude API, which returns a structured GTM brief containing ICP signals, likely pain points, tech stack signals, a recommended outbound angle, and an ICP tier score (A, B, or C).
3. Persists the full brief to a Postgres database via Supabase.
4. Displays results in an interactive Streamlit UI, with a running history of all researched accounts.

The result is a repeatable, one-click research workflow that replaces 20 to 30 minutes of manual desk research per account.

---

## Architecture

```
Input (company name + domain)
        |
        v
[ Scraper ]  src/scraper.py
  Fetches homepage, /about, /pricing via requests.
  Strips scripts, styles, nav, and footer with BeautifulSoup.
  Returns up to 6,000 characters of clean visible text.
        |
        v
[ Researcher ]  src/researcher.py
  Sends scraped content to the Claude API (claude-sonnet-4-6).
  System prompt frames Claude as a senior B2B SaaS GTM analyst.
  Returns a structured JSON brief: ICP signals, pain points,
  tech stack signals, recommended angle, ICP tier, and summary.
        |
        v
[ Database ]  src/database.py
  Saves the combined brief to the "accounts" table in Supabase (Postgres).
  Exposes get_all_accounts() for the history view.
        |
        v
[ Orchestrator ]  src/agent.py
  run_research() wires scraper, researcher, and database together.
  Single entry point called by the UI.
        |
        v
[ UI ]  app.py
  Streamlit app: research form, color-coded ICP tier badge,
  three-column brief display, and a full account history table.
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| AI / LLM | Anthropic Claude API (claude-sonnet-4-6) |
| Database | Supabase (Postgres) |
| Web scraping | requests, BeautifulSoup4 |
| UI | Streamlit |
| Config | python-dotenv |

---

## Setup

### 1. Create and activate a conda environment

```bash
conda create -n gtm-intel python=3.11 -y
conda activate gtm-intel
```

### 2. Install dependencies

```bash
pip install anthropic supabase streamlit requests beautifulsoup4 python-dotenv
```

### 3. Configure environment variables

Create a `.env` file in the project root with the following keys (fill in your own values):

```
ANTHROPIC_API_KEY=your_anthropic_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_or_service_role_key
```

### 4. Create the Supabase table

In the Supabase SQL editor, run:

```sql
create table accounts (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  company_name text,
  domain text,
  homepage_content text,
  icp_signals jsonb,
  pain_points jsonb,
  tech_stack_signals jsonb,
  recommended_angle text,
  icp_tier text,
  summary text,
  raw_brief jsonb
);
```

### 5. Run the app

```bash
streamlit run app.py
```

---

## Roadmap

| Phase | Feature | Status |
|---|---|---|
| Phase 1 | Account research agent: scrape, analyze, score, and store | Done |
| Phase 2 | ICP scoring engine: batch scoring, tier distribution analytics, CRM sync | Planned |
