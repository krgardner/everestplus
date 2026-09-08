# Everest+ Fantasy Football Dashboard

A self-updating website for the Everest+ Sleeper league. No accounts, no apps,
no email — just a link people bookmark and check whenever they want.

**How it works:** a GitHub Action runs every Tuesday morning, pulls live data
from Sleeper's public API, computes power rankings + an all-play luck index,
and writes the results as JSON. The website (hosted free on GitHub Pages)
reads that JSON and displays it. Nobody has to do anything to keep it current.

---

## One-time setup (about 10 minutes)

### 1. Create the GitHub repo
- Go to github.com → New repository → name it something like `everest-ff`
- Public or private both work fine for GitHub Pages (private repos need GitHub
  Pages enabled on a paid plan for Pages — if you want to stay free, make it public;
  nothing in this repo contains secrets, it's all public Sleeper data anyway)
- Don't initialize with a README (we already have one)

### 2. Push these files
```bash
cd everest-ff-site
git init
git add .
git commit -m "Initial dashboard setup"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

### 3. Set your league ID as a repo variable
The scripts default to Everest+'s league ID (`1389378221123833856`), but it's
cleaner to set it as a repo variable so you're not hardcoding it:

- Repo → Settings → Secrets and variables → Actions → **Variables** tab → New repository variable
- Name: `LEAGUE_ID`
- Value: `1389378221123833856`

(If you skip this, the script falls back to the hardcoded default, so it'll
still work either way.)

### 4. Enable GitHub Pages
- Repo → Settings → Pages
- Source: **Deploy from a branch**
- Branch: `main`, folder: `/docs`
- Save

GitHub will give you a URL like `https://<your-username>.github.io/<your-repo>/`
— that's the link you'll share with the league.

### 5. Run the Action for the first time
- Repo → Actions tab → "Update Fantasy Football Data" workflow → **Run workflow**
  (this triggers it manually instead of waiting for Tuesday)
- Wait ~30 seconds, refresh — you should see a new commit updating
  `docs/data/rankings.json`
- Visit your Pages URL — you should see the dashboard populated

If the season hasn't started yet, you'll see a "check back once games are
played" placeholder instead of empty tables — that's expected.

---

## Repo structure

```
.github/workflows/update.yml   — the scheduled Action (runs Tuesdays, or manually)
scripts/sleeper_client.py      — Sleeper API wrapper
scripts/analytics.py           — power rankings + luck index math
scripts/generate_data.py       — entrypoint the Action runs; writes JSON
docs/index.html                — the actual website (served by GitHub Pages)
docs/data/rankings.json        — generated data file (auto-committed by the Action)
requirements.txt               — Python deps (just `requests`)
```

## Customizing the schedule

Edit the `cron` line in `.github/workflows/update.yml`. It's currently set to
`0 10 * * 2` (Tuesday 10:00 UTC). Cron is always UTC, so adjust for your
timezone — e.g. for Wednesday 8am US Eastern (UTC-5 in regular season),
that'd be `0 13 * * 3`. You can also just click "Run workflow" manually
anytime instead of waiting.

## What's next

This ships with Power Rankings + Luck Index. The pipeline is built so adding
more content is just: extend `analytics.py` with a new computation, add its
output to `generate_data.py`'s JSON payload, and add a section to
`docs/index.html` to display it. Good next additions:

- Waiver wire / trade grades (needs `get_transactions()`, already in the client)
- Weekly narrative recap (LLM-generated blurb based on the week's data)
- Styled visual design (current HTML is intentionally bare-bones/functional —
  next pass makes it actually look good)
- Historical/all-time stats (via `get_previous_league_id()` to chain seasons)

Let me know which of these you want built next and I'll extend this same repo.
