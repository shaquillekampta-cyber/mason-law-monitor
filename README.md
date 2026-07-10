# Mason Law — News Monitor

Automated news monitoring dashboard for Mining & Resources, M&A/Corporate, and Securities & Capital Markets practice areas.

## Setup

### 1. Install dependencies

```bash
cd ~/mason-law-monitor
pip install -r requirements.txt
```

### 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add this to your `~/.zshrc` or `~/.bashrc` to make it permanent.

### 3. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## How it works

- On startup, a background scrape runs immediately
- APScheduler re-runs every 6 hours automatically
- Click **Refresh** in the dashboard to trigger a manual scrape
- Articles scoring below 3/10 are filtered out automatically
- Deduplication is by URL — the same article won't appear twice

## Dashboard

| Feature | How to use |
|---|---|
| Filter by practice area | Click area buttons in the left sidebar |
| Filter by score | Click the 3+/5+/7+ buttons |
| Search | Type in the search bar (searches title + summary) |
| Mark as read | Click "Mark read" or click the article link |
| Dismiss | Click "Dismiss" to hide an article |
| Manual refresh | Click the Refresh button in the top bar |

## Score colours

- **Green (7–10)** — Highly relevant, direct connection to practice area
- **Yellow (4–6)** — Moderately relevant
- **Red (0–3)** — Low relevance (filtered out by default, shown if Min Relevance = All)

## Configuration

Edit `config.py` to:
- Add or remove RSS feeds (`RSS_FEEDS`)
- Adjust keywords per practice area (`PRACTICE_AREAS`)
- Change the fetch interval (`FETCH_INTERVAL_HOURS`)
- Change the minimum score threshold (`MIN_RELEVANCE_SCORE`)
