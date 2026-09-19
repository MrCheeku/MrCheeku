#!/usr/bin/env python3
import json
import os
import urllib.request
from datetime import date, timedelta
from html import escape

OWNER = "MrCheeku"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = "dist"
os.makedirs(OUT, exist_ok=True)

def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "MrCheeku-profile-stats",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]

end = date.today()
start = end - timedelta(days=365)
query = f'''
query {{
  user(login: "{OWNER}") {{
    followers {{ totalCount }}
    following {{ totalCount }}
    repositories(first: 1, ownerAffiliations: OWNER, isFork: false) {{ totalCount }}
    contributionsCollection(from: "{start}T00:00:00Z", to: "{end + timedelta(days=1)}T00:00:00Z") {{
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {{
        totalContributions
        weeks {{
          contributionDays {{ date contributionCount }}
        }}
      }}
    }}
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
      nodes {{
        name
        stargazerCount
        languages(first: 8, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{ size node {{ name }} }}
        }}
      }}
    }}
  }}
}}
'''
user = gql(query)
cc = user["contributionsCollection"]
calendar = cc["contributionCalendar"]
days = [d for w in calendar["weeks"] for d in w["contributionDays"]]

def streaks(items):
    dates = {date.fromisoformat(x["date"]) for x in items if x["contributionCount"] > 0}
    if not dates:
        return 0, 0
    best = cur = 0
    d = min(dates)
    while d <= max(dates):
        if d in dates:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
        d += timedelta(days=1)
    current = 0
    d = max(dates)
    while d in dates:
        current += 1
        d -= timedelta(days=1)
    return current, best

current_streak, longest_streak = streaks(days)

lang_sizes = {}
for repo in user["repositories"]["nodes"]:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        lang_sizes[name] = lang_sizes.get(name, 0) + edge["size"]
languages = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:6]
lang_total = max(sum(v for _, v in languages), 1)

repos = user["repositories"]["totalCount"]
followers = user["followers"]["totalCount"]
following = user["following"]["totalCount"]
contribs = calendar["totalContributions"]
commits = cc["totalCommitContributions"]
prs = cc["totalPullRequestContributions"]
issues = cc["totalIssueContributions"]
reviews = cc["totalPullRequestReviewContributions"]

def svg_open(title, w=900, h=260):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<rect width="100%" height="100%" rx="18" fill="#0d1117"/>
<text x="32" y="42" fill="#EF93C4" font-family="Arial,Helvetica,sans-serif" font-size="22" font-weight="700">{escape(title)}</text>'''

def svg_close():
    return "</svg>"

def txt(x,y,s,size=16,fill="#c9d1d9",weight="400",anchor="start"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}">{escape(str(s))}</text>'

def card(x,y,w,h,value,label):
    return f'''<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#161b22" stroke="#30363d"/>
{txt(x+18,y+38,value,28,"#ffffff","700")}
{txt(x+18,y+63,label,13,"#8b949e")}'''

# Stats
s = svg_open("GitHub Stats", 900, 285)
cards = [
    (28,62,198,88,commits,"Commits (1 year)"),
    (238,62,198,88,prs,"Pull Requests"),
    (448,62,198,88,issues,"Issues"),
    (658,62,198,88,reviews,"Reviews"),
]
for a in cards: s += card(*a)
s += card(133,168,198,82,repos,"Public repositories")
s += card(351,168,198,82,followers,"Followers")
s += card(569,168,198,82,following,"Following")
s += svg_close()
open(f"{OUT}/github-stats.svg","w",encoding="utf-8").write(s)

# Streak
s = svg_open("GitHub Streak", 900, 235)
s += card(48,70,240,105,current_streak,"Current streak (days)")
s += card(330,70,240,105,longest_streak,"Longest streak (days)")
s += card(612,70,240,105,contribs,"Contributions (1 year)")
s += txt(450,215,"Contribution data from GitHub's public profile calendar",12,"#8b949e","400","middle")
s += svg_close()
open(f"{OUT}/github-streak.svg","w",encoding="utf-8").write(s)

# Languages
s = svg_open("Most Used Languages", 900, 270)
y = 76
bar_w = 520
for name, size in languages:
    pct = size / lang_total * 100
    label = f"{name}  {pct:.1f}%"
    s += txt(38,y,label,14,"#c9d1d9","600")
    s += f'<rect x="250" y="{y-14}" width="{bar_w}" height="14" rx="7" fill="#21262d"/>'
    s += f'<rect x="250" y="{y-14}" width="{max(8,bar_w*pct/100):.1f}" height="14" rx="7" fill="#EF93C4"/>'
    y += 31
s += txt(450,253,"Based on language bytes across your non-fork repositories",12,"#8b949e","400","middle")
s += svg_close()
open(f"{OUT}/github-languages.svg","w",encoding="utf-8").write(s)

# Achievement / milestones card
s = svg_open("GitHub Achievements & Milestones", 900, 285)
milestones = [
    (28,65,200,88,"🏆", "Contributions", contribs),
    (244,65,200,88,"📦", "Repositories", repos),
    (460,65,200,88,"👥", "Followers", followers),
    (676,65,196,88,"🔥", "Best streak", longest_streak),
]
for x,y,w,h,icon,label,value in milestones:
    s += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#161b22" stroke="#30363d"/>'
    s += txt(x+18,y+35,icon,24)
    s += txt(x+18,y+62,value,24,"#ffffff","700")
    s += txt(x+18,y+80,label,12,"#8b949e")
s += txt(450,204,"Verified from your GitHub contribution/profile data",13,"#8b949e","400","middle")
s += txt(450,228,"Commits  •  Pull Requests  •  Issues  •  Reviews",13,"#8b949e","400","middle")
s += txt(450,255,"Public profile activity only",11,"#6e7681","400","middle")
s += svg_close()
open(f"{OUT}/github-trophies.svg","w",encoding="utf-8").write(s)

# Activity graph
s = svg_open("Contribution Activity", 900, 285)
max_c = max([d["contributionCount"] for d in days] or [1])
step = 830 / max(1,len(days))
x = 35
base = 225
for d in days:
    h = 2 if d["contributionCount"] == 0 else 4 + 130 * (d["contributionCount"]/max_c)
    fill = "#21262d" if d["contributionCount"] == 0 else "#EF93C4"
    s += f'<rect x="{x:.1f}" y="{base-h:.1f}" width="{max(1.2,step-1):.1f}" height="{h:.1f}" rx="2" fill="{fill}"/>'
    x += step
s += f'<line x1="35" y1="{base}" x2="865" y2="{base}" stroke="#30363d"/>'
for i,label in enumerate(["Sep","Dec","Mar","Jun","Sep"]):
    px = 35 + i*207.5
    s += txt(px,250,label,11,"#8b949e")
s += txt(450,270,"Daily contributions over the last year",12,"#8b949e","400","middle")
s += svg_close()
open(f"{OUT}/github-activity.svg","w",encoding="utf-8").write(s)
