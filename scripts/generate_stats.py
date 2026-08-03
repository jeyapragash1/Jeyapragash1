#!/usr/bin/env python3
"""
Fetch GitHub contribution totals via GraphQL and render a simple SVG.

Usage:
  python scripts/generate_stats.py --username <username> --token <PAT> --out stats/github_stats.svg
"""
import argparse, json, sys, requests
GRAPHQL_URL = "https://api.github.com/graphql"
SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="760" height="140">
  <style>
    .bg {{ fill: #0b1220 }} 
    .card {{ fill: #0f1724; stroke: #111827; stroke-width:1 }}
    .title {{ fill: #66d9ef; font-family: Inter, Roboto, sans-serif; font-size:18px; font-weight:700 }}
    .label {{ fill: #94a3b8; font-family: Inter, Roboto, sans-serif; font-size:12px }}
    .value {{ fill: #e6eef8; font-family: Inter, Roboto, sans-serif; font-size:28px; font-weight:700 }}
  </style>
  <rect class="bg" width="100%" height="100%" rx="8"/>
  <rect class="card" x="12" y="12" width="736" height="116" rx="6"/>
  <text x="36" y="40" class="title">K. Jeyapragash's GitHub Summary</text>
  <text x="36" y="70" class="label">Total contributions (year):</text>
  <text x="260" y="70" class="value">{year_total}</text>
  <text x="36" y="98" class="label">Total commits (all time - GraphQL):</text>
  <text x="320" y="98" class="value">{commit_total}</text>
  <text x="36" y="126" class="label">Restricted/private contributions (this year):</text>
  <text x="360" y="126" class="value">{restricted}</text>
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
    return {
        "year_total": c.get("contributionCalendar", {}).get("totalContributions", 0),
        "commit_total": c.get("totalCommitContributions", 0),
        "restricted": c.get("restrictedContributionsCount", 0),
    }
def render_svg(stats, out_path):
    svg = SVG_TEMPLATE.format(year_total=stats["year_total"], commit_total=stats["commit_total"], restricted=stats["restricted"])
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
