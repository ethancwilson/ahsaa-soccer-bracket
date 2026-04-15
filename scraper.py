#!/usr/bin/env python3
"""
AHSAA Boys Soccer Bracket Generator
Fetches live standings from scorbord.com and generates index.html
Run manually or automatically via GitHub Actions every 2 hours.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
import sys

# ── scorbord.com classification IDs ─────────────────────────────────────────
CLASSIFICATIONS = [
    {
        "id": 1670, "name": "7A",    "slug": "c7a",
        "areas": 8,  "bracket": 16,
        "r1_date": "April 27–28", "r2_date": "April 30–May 2",
        "deadline": "April 22",
    },
    {
        "id": 1671, "name": "6A",    "slug": "c6a",
        "areas": 16, "bracket": 32,
        "r1_date": "April 23–25", "r2_date": "April 27–28",
        "deadline": "April 18",
    },
    {
        "id": 1672, "name": "5A",    "slug": "c5a",
        "areas": 16, "bracket": 32,
        "r1_date": "April 23–25", "r2_date": "April 27–28",
        "deadline": "April 18",
    },
    {
        "id": 1673, "name": "4A",    "slug": "c4a",
        "areas": 8,  "bracket": 16,
        "r1_date": "April 27–28", "r2_date": "April 30–May 2",
        "deadline": "April 22",
    },
    {
        "id": 1674, "name": "1A–3A", "slug": "c13a",
        "areas": 8,  "bracket": 16,
        "r1_date": "April 27–28", "r2_date": "April 30–May 2",
        "deadline": "April 22",
    },
]

# ── Bracket matchup order from AHSAA Sports Book ────────────────────────────
# Each tuple is (host_area, host_seed, visitor_area, visitor_seed)
# seed 1 = winner, seed 2 = runner-up
BRACKET_16 = [
    # Top half
    (1, 1, 2, 2), (4, 1, 3, 2), (2, 1, 1, 2), (3, 1, 4, 2),
    # Bottom half
    (5, 1, 6, 2), (8, 1, 7, 2), (6, 1, 5, 2), (7, 1, 8, 2),
]

# 32-team bracket: quadrants (areas 5-8), (areas 1-4), (areas 13-16), (areas 9-12)
BRACKET_32 = [
    # Q1 – Areas 5-8
    (5, 1, 6, 2), (8, 1, 7, 2), (6, 1, 5, 2), (7, 1, 8, 2),
    # Q2 – Areas 1-4
    (1, 1, 2, 2), (4, 1, 3, 2), (2, 1, 1, 2), (3, 1, 4, 2),
    # Q3 – Areas 13-16
    (13, 1, 14, 2), (16, 1, 15, 2), (14, 1, 13, 2), (15, 1, 16, 2),
    # Q4 – Areas 9-12
    (9, 1, 10, 2), (12, 1, 11, 2), (10, 1, 9, 2), (11, 1, 12, 2),
]

BRACKET_32_QUADRANT_LABELS = {
    0: "QUADRANT 1 — Areas 5–8",
    4: "QUADRANT 2 — Areas 1–4",
    8: "QUADRANT 3 — Areas 13–16",
    12: "QUADRANT 4 — Areas 9–12",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


# ── Data fetching & parsing ──────────────────────────────────────────────────

def parse_record(text):
    """'9 - 12 - 0' → (9, 12, 0)"""
    parts = [p.strip() for p in text.split("-")]
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return (0, 0, 0)


def win_pct(w, l, t):
    """Win percentage treating ties as half a win. Returns -1 if no games."""
    total = w + l + t
    if total == 0:
        return -1.0
    return (w + 0.5 * t) / total


def fmt_rec(w, l, t):
    return f"{w}-{l}-{t}"


def fetch_areas(class_id):
    """
    Fetches a scorbord.com classification page and returns a dict:
      { area_num (int): [sorted list of team dicts], ... }
    Teams are sorted by area win%, then area wins descending.
    """
    url = f"https://www.scorbord.com/classifications/{class_id}/teams"
    print(f"  Fetching {url} ...", end=" ", flush=True)

    resp = requests.get(url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    print("OK")

    soup = BeautifulSoup(resp.text, "html.parser")
    teams_list = soup.find(class_="teams_list")
    if not teams_list:
        print("  WARNING: .teams_list not found!", file=sys.stderr)
        return {}

    areas = {}
    for team_el in teams_list.find_all(class_="team"):
        name_el   = team_el.find(class_="name")
        record_el = team_el.find(class_="record")
        conf_el   = team_el.find(class_="conference")

        if not (name_el and record_el and conf_el):
            continue

        name = name_el.get_text(strip=True)

        overall_el  = record_el.find(class_="overall")
        area_rec_el = record_el.find(class_="conference")

        overall  = parse_record(overall_el.get_text(strip=True))  if overall_el  else (0, 0, 0)
        area_rec = parse_record(area_rec_el.get_text(strip=True)) if area_rec_el else (0, 0, 0)

        area_text = conf_el.get_text(strip=True)
        m = re.search(r"(\d+)", area_text)
        if not m:
            continue
        area_num = int(m.group(1))

        areas.setdefault(area_num, []).append({
            "name":     name,
            "overall":  overall,
            "area_rec": area_rec,
            "area_pct": win_pct(*area_rec),
        })

    # Sort each area: by area_pct desc, then area wins desc
    for a in areas:
        areas[a].sort(key=lambda t: (t["area_pct"], t["area_rec"][0]), reverse=True)

    return areas


# ── HTML generation helpers ──────────────────────────────────────────────────

def is_tied(teams, idx):
    """True if team at idx has same pct as the next team (tie for that seed)."""
    if idx + 1 >= len(teams):
        return False
    if teams[idx]["area_pct"] < 0 and teams[idx + 1]["area_pct"] < 0:
        return True  # both 0 games
    if teams[idx]["area_pct"] < 0 or teams[idx + 1]["area_pct"] < 0:
        return False
    return abs(teams[idx]["area_pct"] - teams[idx + 1]["area_pct"]) < 0.0001


def area_standings_html(area_num, teams):
    """Renders one area standings box."""
    rows = ""
    for i, t in enumerate(teams):
        w, l, tr = t["area_rec"]
        ow, ol, ot = t["overall"]
        tied = is_tied(teams, i) or (i > 0 and is_tied(teams, i - 1))

        if i == 0:
            if is_tied(teams, 0):
                badge = '<span class="badge-tbd">TBD</span>'
                row_class = ""
            else:
                badge = '<span class="badge-w">W</span>'
                row_class = 'class="winner"'
        elif i == 1:
            if is_tied(teams, 0):
                badge = '<span class="badge-tbd">TBD</span>'
                row_class = ""
            elif is_tied(teams, 1):
                badge = '<span class="badge-tbd">RU?</span>'
                row_class = 'class="runnerup"'
            else:
                badge = '<span class="badge-ru">RU</span>'
                row_class = 'class="runnerup"'
        else:
            badge = ""
            row_class = ""

        rows += f"""        <tr {row_class}>
          <td>{t['name']}{badge}</td>
          <td>{fmt_rec(w,l,tr)}</td>
          <td>{fmt_rec(ow,ol,ot)}</td>
        </tr>\n"""

    return f"""    <div class="area-box">
      <div class="area-header">Area {area_num}</div>
      <table class="area-table">
        <tr><th>School</th><th>Area</th><th>Overall</th></tr>
{rows}      </table>
    </div>"""


def bracket_slot(area_num, seed_idx, areas, position_class):
    """
    Renders one team slot (top or bottom) inside a bracket matchup.
    seed_idx: 0 = winner, 1 = runner-up
    """
    seed_label = "Winner" if seed_idx == 0 else "Runner-Up"
    teams = areas.get(area_num, [])

    if len(teams) <= seed_idx:
        return f"""        <div class="team-slot {position_class} slot-tbd">
          <span class="team-name">TBD – Area {area_num} {seed_label}</span>
          <span class="team-seed">A{area_num} {seed_label}</span>
        </div>"""

    team = teams[seed_idx]
    w, l, t = team["area_rec"]
    total = w + l + t

    tied = is_tied(teams, seed_idx) or (seed_idx > 0 and is_tied(teams, seed_idx - 1))

    if total == 0 or tied:
        badge = '<span class="badge-tbd">TBD</span>'
        css = "slot-tbd"
        name_display = team["name"]
        # If tied, show both names
        if tied and seed_idx == 0 and len(teams) > 1:
            name_display = f"{teams[0]['name']} / {teams[1]['name']}"
    elif seed_idx == 0:
        badge = '<span class="badge-w">W</span>'
        css = "slot-winner"
        name_display = team["name"]
    else:
        badge = '<span class="badge-ru">RU</span>'
        css = "slot-ru"
        name_display = team["name"]

    return f"""        <div class="team-slot {position_class} {css}">
          <span class="team-name">{name_display}{badge}</span>
          <span class="team-seed">A{area_num} {seed_label} · {fmt_rec(w,l,t)} area</span>
        </div>"""


def bracket_matchups_html(matchups, areas, quadrant_labels=None):
    """Renders all matchup rows for a bracket."""
    html = ""
    open_group = False

    for i, (h_area, h_seed, v_area, v_seed) in enumerate(matchups):
        # Open quadrant group if needed
        if quadrant_labels and i in quadrant_labels:
            if open_group:
                html += "    </div>\n\n"
            html += f"""    <div class="bracket-group">
      <div class="bracket-group-title">{quadrant_labels[i]}</div>\n"""
            open_group = True
        elif not quadrant_labels and i == 0:
            html += """    <div class="bracket-group">
      <div class="bracket-group-title">TOP HALF — R1 winners advance to R2</div>\n"""
            open_group = True
        elif not quadrant_labels and i == 4:
            html += "    </div>\n\n"
            html += """    <div class="bracket-group">
      <div class="bracket-group-title">BOTTOM HALF — R1 winners advance to R2</div>\n"""

        host_slot   = bracket_slot(h_area, h_seed - 1, areas, "top")
        visitor_slot = bracket_slot(v_area, v_seed - 1, areas, "")

        html += f"""      <div class="match-row">
        <div class="match-num">{i + 1}</div>
        <div class="match-teams">
{host_slot}
{visitor_slot}
        </div>
        <div class="match-connector">→</div>
      </div>\n"""

    if open_group:
        html += "    </div>\n"

    return html


# ── Full HTML page ───────────────────────────────────────────────────────────

CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; font-size: 13px; }
  h1 { text-align: center; padding: 18px 10px 6px; color: #fff; font-size: 22px; letter-spacing: 1px; }
  .subtitle { text-align: center; color: #aaa; font-size: 12px; padding-bottom: 4px; }
  .updated { text-align: center; color: #666; font-size: 11px; padding-bottom: 14px; }
  .tabs { display: flex; justify-content: center; gap: 6px; padding: 10px; flex-wrap: wrap; }
  .tab { padding: 8px 22px; border-radius: 20px; cursor: pointer; font-weight: bold; font-size: 13px;
         background: #2c2c54; color: #aaa; border: 2px solid #444; transition: all .2s; }
  .tab.active { background: #e63946; color: #fff; border-color: #e63946; }
  .tab:hover:not(.active) { background: #3a3a6e; color: #fff; }
  .section { display: none; padding: 10px 16px 30px; max-width: 1400px; margin: 0 auto; }
  .section.active { display: block; }
  .section-title { font-size: 18px; font-weight: bold; text-align: center; color: #f1c40f;
                   padding: 10px 0 4px; letter-spacing: 1px; }
  .deadline { text-align: center; color: #aaa; font-size: 11px; margin-bottom: 16px; }
  .areas-grid { display: grid; gap: 10px; margin-bottom: 22px; }
  .col2 { grid-template-columns: repeat(2, 1fr); }
  .col4 { grid-template-columns: repeat(4, 1fr); }
  @media(max-width:900px){.col4{grid-template-columns:repeat(2,1fr);}.col2{grid-template-columns:1fr;}}
  .area-box { background: #16213e; border-radius: 8px; border: 1px solid #2c2c54; overflow: hidden; }
  .area-header { background: #0f3460; padding: 6px 10px; font-weight: bold; font-size: 12px; color: #f1c40f; }
  .area-table { width: 100%; border-collapse: collapse; }
  .area-table th { background: #0a1931; color: #888; font-size: 10px; padding: 3px 6px; text-align: left; }
  .area-table td { padding: 4px 6px; border-top: 1px solid #1e2a40; font-size: 11px; }
  .area-table tr.winner td { color: #2ecc71; font-weight: bold; }
  .area-table tr.runnerup td { color: #3498db; }
  .area-table tr.winner td:first-child::before { content: "\ud83e\udd47 "; }
  .area-table tr.runnerup td:first-child::before { content: "\ud83e\udd48 "; }
  .badge-w  { display:inline-block; background:#2ecc71; color:#000; font-size:9px; border-radius:3px; padding:1px 4px; margin-left:4px; font-weight:bold; }
  .badge-ru { display:inline-block; background:#3498db; color:#000; font-size:9px; border-radius:3px; padding:1px 4px; margin-left:4px; font-weight:bold; }
  .badge-tbd{ display:inline-block; background:#e67e22; color:#000; font-size:9px; border-radius:3px; padding:1px 4px; margin-left:4px; font-weight:bold; }
  .bracket-title { font-size:15px; font-weight:bold; text-align:center; color:#e0e0e0;
                   margin:18px 0 10px; padding:8px; background:#0f3460; border-radius:6px; }
  .bracket-wrap { overflow-x: auto; }
  .bracket-container { display: flex; flex-direction: column; gap: 20px; }
  .bracket-group { background:#16213e; border-radius:8px; border:1px solid #2c2c54; overflow:hidden; }
  .bracket-group-title { background:#0f3460; padding:6px 12px; font-size:11px; color:#f1c40f; font-weight:bold; }
  .match-row { display:flex; align-items:stretch; border-top:1px solid #1e2a40; }
  .match-row:first-of-type { border-top:none; }
  .match-num { width:28px; background:#0a1931; display:flex; align-items:center;
               justify-content:center; color:#888; font-size:10px; flex-shrink:0; }
  .match-teams { flex:1; display:flex; flex-direction:column; }
  .team-slot { padding:5px 10px; display:flex; align-items:center; justify-content:space-between; min-height:28px; }
  .team-slot.top { border-bottom:1px dashed #2c2c54; }
  .team-name { font-size:12px; }
  .team-seed { font-size:10px; color:#888; margin-left:6px; white-space:nowrap; }
  .slot-winner { background:rgba(46,204,113,0.08); }
  .slot-ru     { background:rgba(52,152,219,0.08); }
  .slot-tbd    { background:rgba(230,126,18,0.08); }
  .match-connector { width:30px; display:flex; align-items:center; justify-content:center;
                     color:#444; font-size:18px; flex-shrink:0; }
  .legend { display:flex; gap:14px; justify-content:center; flex-wrap:wrap;
            padding:10px; font-size:11px; color:#aaa; margin-bottom:14px; }
  .legend-item { display:flex; align-items:center; gap:5px; }
  .legend-dot  { width:10px; height:10px; border-radius:2px; }
"""

JS = """
function showClass(id, el) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
}
"""


def build_section(cls, areas, is_active=False):
    slug      = cls["slug"]
    name      = cls["name"]
    deadline  = cls["deadline"]
    r1_date   = cls["r1_date"]
    num_areas = cls["areas"]
    bracket_n = cls["bracket"]
    active_class = " active" if is_active else ""

    grid_cols = "col4" if num_areas >= 8 else "col2"

    # Area standings
    standings_html = ""
    for a in sorted(areas.keys()):
        standings_html += area_standings_html(a, areas[a]) + "\n"

    # Bracket matchups
    if bracket_n == 16:
        matchup_html = bracket_matchups_html(BRACKET_16, areas)
        bracket_label = "16-team Sub-State Bracket"
    else:
        matchup_html = bracket_matchups_html(BRACKET_32, areas, BRACKET_32_QUADRANT_LABELS)
        bracket_label = "32-team Sub-State Bracket"

    return f"""
<div id="{slug}" class="section{active_class}">
  <div class="section-title">CLASS {name} — Boys Soccer</div>
  <div class="deadline">Area deadline: {deadline} &nbsp;·&nbsp; Sub-State R1: {r1_date} &nbsp;·&nbsp; Area winner hosts runner-up</div>
  <div class="areas-grid {grid_cols}">
{standings_html}  </div>
  <div class="bracket-title">{name} {bracket_label} — Round 1 ({r1_date})</div>
  <div class="bracket-wrap">
  <div class="bracket-container">
{matchup_html}  </div>
  </div>
</div>"""


def build_html(all_data, generated_at):
    tabs_html = ""
    sections_html = ""

    for i, cls in enumerate(CLASSIFICATIONS):
        active = "active" if i == 0 else ""
        tabs_html += f'  <div class="tab {active}" onclick="showClass(\'{cls["slug"]}\', this)">{cls["name"]}</div>\n'
        sections_html += build_section(cls, all_data[cls["slug"]], is_active=(i == 0))

    ts = generated_at.strftime("%B %d, %Y at %I:%M %p UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2026 AHSAA Boys Soccer — Area Standings & Playoff Brackets</title>
<style>{CSS}</style>
</head>
<body>

<h1>2026 AHSAA Boys Soccer</h1>
<p class="subtitle">Live area standings &amp; projected sub-state brackets · Data: scorbord.com · Structure: AHSAA Sports Book</p>
<p class="updated">Last updated: {ts}</p>

<div class="tabs">
{tabs_html}</div>

<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#2ecc71"></div> Area Winner (current)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#3498db"></div> Runner-Up (current)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#e67e22"></div> Still being decided (TBD)</div>
</div>

{sections_html}

<script>{JS}</script>
</body>
</html>"""


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("AHSAA Boys Soccer Bracket Generator")
    print("=" * 40)

    all_data = {}
    for cls in CLASSIFICATIONS:
        print(f"\nFetching Class {cls['name']}...")
        try:
            areas = fetch_areas(cls["id"])
            print(f"  Found {len(areas)} areas, "
                  f"{sum(len(v) for v in areas.values())} teams.")
            all_data[cls["slug"]] = areas
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            all_data[cls["slug"]] = {}

    generated_at = datetime.now(timezone.utc)
    html = build_html(all_data, generated_at)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n\u2713 index.html written ({len(html):,} bytes)")
    print(f"  Generated at {generated_at.strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()
