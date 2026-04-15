# 2026 AHSAA Boys Soccer — Live Bracket

A self-updating website that pulls live area standings from [scorbord.com](https://scorbord.com) every 2 hours and regenerates the playoff bracket for all five AHSAA classifications (7A, 6A, 5A, 4A, 1A–3A).

Hosted free on **GitHub Pages**. No server required.

---

## One-Time Setup (~5 minutes)

### 1. Create a GitHub account
Go to [github.com](https://github.com) and sign up if you don't have one.

### 2. Create a new repository
- Click the **+** button → **New repository**
- Name it something like `ahsaa-soccer-bracket`
- Set it to **Public** (required for free GitHub Pages)
- Click **Create repository**

### 3. Upload these files
- Click **uploading an existing file** on the repo page
- Drag and drop **all files from this ZIP** (keeping the folder structure)
- Click **Commit changes**

### 4. Enable GitHub Pages
- Go to your repo → **Settings** → **Pages** (left sidebar)
- Under **Source**, select **Deploy from a branch**
- Branch: **main** / Folder: **/ (root)**
- Click **Save**
- Your site will be live at: `https://YOUR-USERNAME.github.io/ahsaa-soccer-bracket/`

### 5. Run it once manually
- Go to the **Actions** tab in your repo
- Click **Update Brackets** in the left list
- Click **Run workflow** → **Run workflow**
- Wait ~30 seconds — it will scrape scorbord.com and commit `index.html`
- Visit your GitHub Pages URL to see the live site!

---

## How It Works

Every 2 hours, GitHub Actions triggers scraper.py, which fetches the five scorbord.com pages (one per classification), parses team names and records, sorts each area by win percentage, generates index.html with updated standings and bracket, then commits and pushes to GitHub. GitHub Pages serves the updated site automatically.

## Changing the Update Frequency

Edit `.github/workflows/update.yml` and change the cron expression:
- `0 */2 * * *` — every 2 hours (current)
- `0 * * * *` — every hour
- `*/30 * * * *` — every 30 minutes
- `0 12 * * *` — once daily at noon UTC

## Running Locally

```bash
pip install requests beautifulsoup4
python scraper.py
```

## Classification IDs on scorbord.com

| Class | scorbord ID | Areas | Bracket |
|-------|-------------|-------|---------|
| 7A    | 1670        | 8     | 16-team |
| 6A    | 1671        | 16    | 32-team |
| 5A    | 1672        | 16    | 32-team |
| 4A    | 1673        | 8     | 16-team |
| 1A–3A | 1674       | 8     | 16-team |

Bracket matchup order follows the **2026 AHSAA Sports Book** (pages 171–172).
