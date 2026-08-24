#!/usr/bin/env python3
"""
Fetch GitHub contribution totals & top languages via GraphQL and render styled SVGs.

Usage:
  python scripts/generate_stats.py --username <username> --token <PAT> --out stats/github_stats.svg
"""
import argparse, json, sys, requests

GRAPHQL_URL = "https://api.github.com/graphql"

SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="760" height="200" viewBox="0 0 760 200" fill="none">
  <style>
    .bg {{ fill: #0b1220; rx: 10px; }} 
    .card {{ fill: #0f172a; stroke: #1e293b; stroke-width: 1.5; rx: 8px; }}
    .title {{ fill: #38bdf8; font-family: 'Inter', -apple-system, sans-serif; font-size: 18px; font-weight: 700; }}
    .sub {{ fill: #94a3b8; font-family: 'Inter', -apple-system, sans-serif; font-size: 13px; }}
    .label {{ fill: #cbd5e1; font-family: 'Inter', -apple-system, sans-serif; font-size: 13px; font-weight: 500; }}
    .value {{ fill: #f8fafc; font-family: 'Inter', -apple-system, sans-serif; font-size: 20px; font-weight: 700; }}
    .lang-title {{ fill: #38bdf8; font-family: 'Inter', -apple-system, sans-serif; font-size: 14px; font-weight: 600; }}
    .lang-name {{ fill: #e2e8f0; font-family: 'Inter', -apple-system, sans-serif; font-size: 12px; }}
    .lang-pct {{ fill: #94a3b8; font-family: 'Inter', -apple-system, sans-serif; font-size: 12px; }}
  </style>
  <rect class="bg" width="100%" height="100%"/>
  <rect class="card" x="12" y="12" width="736" height="176"/>
  
  <!-- Header -->
  <text x="32" y="42" class="title">⚡ Kisho Jeyapragash — GitHub Telemetry & Stats</text>
  <text x="32" y="62" class="sub">Automated GraphQL Data Sync</text>
  
  <!-- Stat Columns -->
  <text x="32" y="95" class="label">Total Contributions (Year):</text>
  <text x="32" y="120" class="value">{year_total}</text>
  
  <text x="240" y="95" class="label">GraphQL Commit Total:</text>
  <text x="240" y="120" class="value">{commit_total}</text>
  
  <text x="440" y="95" class="label">Private Contributions:</text>
  <text x="440" y="120" class="value">{restricted}</text>

  <!-- Languages Bar -->
  <text x="32" y="150" class="lang-title">Top Languages:</text>
  {lang_elements}
</svg>"""

def query_graphql(token, query, variables=None):
    headers = {"Authorization": f"bearer {token}"}
    resp = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables or {}}, headers=headers, timeout=30)
    if resp.status_code != 200:
        print("GraphQL request failed:", resp.status_code, resp.text, file=sys.stderr)
        resp.raise_for_status()
    return resp.json()

def fetch_contributions(username, token):
    query = '''
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar { totalContributions }
          totalCommitContributions
          restrictedContributionsCount
        }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
      }
    }
    '''
    data = query_graphql(token, query, {"login": username})
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"]))
    user = data.get("data", {}).get("user")
    if not user:
        raise RuntimeError("User not found in GraphQL response")
    c = user["contributionsCollection"]
    
    # Calculate top languages
    lang_totals = {}
    lang_colors = {}
    for repo in user.get("repositories", {}).get("nodes", []):
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            color = edge["node"]["color"] or "#38bdf8"
            size = edge["size"]
            lang_totals[name] = lang_totals.get(name, 0) + size
            lang_colors[name] = color
            
    total_size = sum(lang_totals.values()) or 1
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    top_langs = [
        {"name": name, "pct": round((size / total_size) * 100, 1), "color": lang_colors[name]}
        for name, size in sorted_langs
    ]
    
    return {
        "year_total": c.get("contributionCalendar", {}).get("totalContributions", 0),
        "commit_total": c.get("totalCommitContributions", 0),
        "restricted": c.get("restrictedContributionsCount", 0),
        "top_langs": top_langs
    }

def render_svg(stats, out_path):
    lang_items = []
    x_offset = 150
    for l in stats["top_langs"]:
        color = l["color"]
        name = l["name"]
        pct = f'{l["pct"]}%'
        lang_items.append(
            f'<circle cx="{x_offset}" cy="146" r="5" fill="{color}"/>'
            f'<text x="{x_offset + 10}" y="150" class="lang-name">{name}</text>'
            f'<text x="{x_offset + 10 + len(name)*7 + 5}" y="150" class="lang-pct">({pct})</text>'
        )
        x_offset += len(name)*7 + len(pct)*7 + 45
        
    lang_elements = "\n  ".join(lang_items) if lang_items else '<text x="150" y="150" class="lang-name">JavaScript, Python, TypeScript, PHP</text>'
    
    svg = SVG_TEMPLATE.format(
        year_total=f"{stats['year_total']:,}",
        commit_total=f"{stats['commit_total']:,}",
        restricted=f"{stats['restricted']:,}",
        lang_elements=lang_elements
    )
    open(out_path, "w", encoding="utf-8").write(svg)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--username", required=True)
    p.add_argument("--token", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    stats = fetch_contributions(args.username, args.token)
    from pathlib import Path
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render_svg(stats, str(out))
    print("Wrote:", out)

if __name__ == '__main__':
    main()
