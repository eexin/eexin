#!/usr/bin/env python3
"""Render assets/stats.svg — a HUD-style GitHub stats panel.

Runs daily in GitHub Actions (see .github/workflows/update-stats.yml).
Uses only the Python standard library. Locally:  python scripts/build_stats.py --sample
"""
import base64, datetime, json, os, pathlib, re, sys, urllib.error, urllib.request

USER = "eexin"
EXCLUDE = {"eexin"}          # repos to leave out of the numbers (the profile repo itself)
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "stats.svg"
FONTS = ROOT / "assets" / "fonts"

LANG_COLORS = {
    "TypeScript": "#3178C6", "JavaScript": "#F1E05A", "Python": "#3572A5", "C#": "#178600", "PHP": "#4F5D95",
    "Java": "#B07219", "C++": "#F34B7D", "C": "#555555", "HTML": "#E34C26", "CSS": "#663399", "ASP.NET": "#9400FF",
    "Shell": "#89E051", "PLpgSQL": "#336790", "TSQL": "#E38C00", "Jupyter Notebook": "#DA5B0B", "Dockerfile": "#384D54",
}
BG, BG2, PANEL, CY, CY_DIM, CY_DEEP, AMB, WHITE, BODY, MUTED = (
    "#02040A", "#04101A", "#061520", "#00E5FF", "#4FA9BC", "#0E3A48", "#FFB020", "#EFFCFF", "#B8DCE6", "#5E8C99")
MONO, ORB = "'Share Tech Mono',ui-monospace,monospace", "'Orbitron',sans-serif"

# ----------------------------------------------------------------- data
def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"{USER}-profile-stats",
        **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r), r.headers.get("Link", "")
    except urllib.error.HTTPError as e:
        if e.code == 409:   # empty repository
            return [], ""
        raise

def fetch():
    repos, _ = api(f"/users/{USER}/repos?per_page=100&type=owner")
    repos = [r for r in repos if not r["fork"] and r["name"] not in EXCLUDE]
    langs, commits = {}, 0
    for r in repos:
        for k, v in api(f"/repos/{USER}/{r['name']}/languages")[0].items():
            langs[k] = langs.get(k, 0) + v
        data, link = api(f"/repos/{USER}/{r['name']}/commits?author={USER}&per_page=1")
        m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
        commits += int(m.group(1)) if m else len(data)
    return {"repos": len(repos), "stars": sum(r["stargazers_count"] for r in repos), "commits": commits,
            "langs": langs, "basis": "BY CODE SIZE", "updated": datetime.date.today().isoformat(), "live": True}

SAMPLE = {"repos": 6, "stars": 4, "commits": None, "basis": "BY REPOSITORY", "live": False,
          "langs": {"TypeScript": 2, "C#": 1, "PHP": 1, "Python": 1, "JavaScript": 1},
          "updated": datetime.date.today().isoformat()}

# ----------------------------------------------------------------- render
def font_css():
    out = []
    for fam, w, f in [("Orbitron", 700, "orbitron-700.woff2"), ("Orbitron", 900, "orbitron-900.woff2"), ("Share Tech Mono", 400, "share-tech-mono.woff2")]:
        p = FONTS / f
        if p.exists():
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url(data:font/woff2;base64,{base64.b64encode(p.read_bytes()).decode()}) format('woff2')}}")
    return "".join(out)

def cut(x, y, w, h, c=14):
    return f"M{x+c} {y}H{x+w-c}L{x+w} {y+c}V{y+h-c}L{x+w-c} {y+h}H{x+c}L{x} {y+h-c}V{y+c}Z"

def render(d):
    total = sum(d["langs"].values()) or 1
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])
    top, rest = items[:7], sum(v for _, v in items[7:])
    if rest: top.append(("Other", rest))

    tiles = [("PUBLIC REPOS", d["repos"]), ("STARS EARNED", d["stars"]),
             ("COMMITS", "—" if d["commits"] is None else d["commits"]), ("LANGUAGES", len(d["langs"]))]
    t_svg = []
    for i, (lab, val) in enumerate(tiles):
        x, y = 36 + (i % 2) * 262, 66 + (i // 2) * 104
        t_svg.append(f'<path d="{cut(x, y, 248, 90, 10)}" fill="{PANEL}" stroke="{CY_DEEP}"/>'
                     f'<rect x="{x}" y="{y+16}" width="3" height="58" fill="{CY if i != 1 else AMB}"/>'
                     f'<text x="{x+22}" y="{y+52}" font-family="{ORB}" font-weight="900" font-size="40" fill="{WHITE}">{val}</text>'
                     f'<text x="{x+22}" y="{y+77}" font-family="{MONO}" font-size="14" fill="{MUTED}" letter-spacing="3">{lab}</text>')

    bx, bw, by = 600, 564, 104
    segs, cx = [], bx
    for name, v in top:
        w = bw * v / total
        segs.append(f'<rect x="{cx:.2f}" y="{by}" width="{max(w-2, 1):.2f}" height="14" fill="{LANG_COLORS.get(name, "#8B949E")}"/>')
        cx += w
    legend = []
    for i, (name, v) in enumerate(top):
        x, y = bx + (i % 2) * 290, 154 + (i // 2) * 30
        legend.append(f'<rect x="{x}" y="{y-12}" width="12" height="12" fill="{LANG_COLORS.get(name, "#8B949E")}"/>'
                      f'<text x="{x+20}" y="{y}" font-family="{MONO}" font-size="17" fill="{BODY}">{name}</text>'
                      f'<text x="{x+262}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="17" fill="{CY_DIM}">{100*v/total:.1f}%</text>')
    status = f"UPDATED {d['updated']}  ·  REFRESHES DAILY" if d["live"] else "PREVIEW DATA  ·  REFRESHES ON FIRST ACTION RUN"

    body = f'''<rect width="1200" height="300" fill="{BG}"/>
<path d="{cut(12, 12, 1176, 276, 16)}" fill="{BG2}" stroke="{CY}" stroke-opacity=".55" stroke-width="1.4"/>
<g fill="none" stroke="{CY}" stroke-width="2"><path d="M4 40V4H40"/><path d="M1160 4H1196V40"/><path d="M4 260V296H40"/><path d="M1160 296H1196V260"/></g>
<text x="36" y="47" font-family="{MONO}" font-size="15" fill="{CY_DIM}" letter-spacing="3">GITHUB · {USER.upper()}</text>
<text x="1164" y="47" text-anchor="end" font-family="{MONO}" font-size="13" fill="{CY_DIM}" letter-spacing="2">{status}</text>
{"".join(t_svg)}
<line x1="568" y1="66" x2="568" y2="260" stroke="{CY}" stroke-opacity=".3"/>
<text x="{bx}" y="88" font-family="{MONO}" font-size="14" fill="{AMB}" letter-spacing="3">MOST USED LANGUAGES · {d["basis"]}</text>
<rect x="{bx}" y="{by}" width="{bw}" height="14" fill="{PANEL}"/>{"".join(segs)}
{"".join(legend)}'''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 300" width="1200" height="300">'
            f'<style>{font_css()}</style>{body}</svg>')

if __name__ == "__main__":
    data = SAMPLE if "--sample" in sys.argv else fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  repos={data['repos']} stars={data['stars']} commits={data['commits']} langs={len(data['langs'])}")
