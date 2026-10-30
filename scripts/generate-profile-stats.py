#!/usr/bin/env python3
"""Generate self-hosted, neon-styled GitHub profile statistics.

Requires only Python's standard library and a GitHub Actions GITHUB_TOKEN.
Generated SVG files are written to ./dist for the profile-assets workflow.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import date, timedelta
from html import escape

OWNER = "MrCheeku"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = "dist"
API_URL = "https://api.github.com/graphql"

os.makedirs(OUT, exist_ok=True)


def gql(query):
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required to generate profile statistics.")

    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "MrCheeku-profile-stats",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub GraphQL returned HTTP {error.code}: {detail[:500]}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach GitHub GraphQL: {error}") from error

    errors = payload.get("errors")
    if errors:
        messages = "; ".join(item.get("message", "Unknown GraphQL error") for item in errors)
        raise RuntimeError(f"GitHub GraphQL query failed: {messages}")

    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user '{OWNER}' was not returned by the API.")
    return user


end = date.today()
start = end - timedelta(days=365)

# Fetch repository count and language data in one repositories selection.
# Selecting the same GraphQL field twice with different arguments causes a
# fieldConflict error, which previously stopped the entire profile workflow.
query = f"""
query {{
  user(login: "{OWNER}") {{
    followers {{ totalCount }}
    following {{ totalCount }}
    contributionsCollection(from: "{start}T00:00:00Z", to: "{end + timedelta(days=1)}T00:00:00Z") {{
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar {{
        totalContributions
        weeks {{
          contributionDays {{ date contributionCount }}
        }}
      }}
    }}
    repositories(
      first: 100,
      ownerAffiliations: OWNER,
      isFork: false,
      orderBy: {{field: UPDATED_AT, direction: DESC}}
    ) {{
      totalCount
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
"""

user = gql(query)
contributions = user["contributionsCollection"]
calendar = contributions["contributionCalendar"]
days = [
    contribution_day
    for week in calendar["weeks"]
    for contribution_day in week["contributionDays"]
]


def calculate_streaks(items, today):
    active_dates = {
        date.fromisoformat(item["date"])
        for item in items
        if item["contributionCount"] > 0
    }
    if not active_dates:
        return 0, 0

    best = current = 0
    cursor = min(active_dates)
    while cursor <= max(active_dates):
        if cursor in active_dates:
            current += 1
            best = max(best, current)
        else:
            current = 0
        cursor += timedelta(days=1)

    # A current streak can include today or yesterday. Do not report an old
    # streak as current when the most recent contribution is several days old.
    anchor = today if today in active_dates else today - timedelta(days=1)
    current_streak = 0
    cursor = anchor
    while cursor in active_dates:
        current_streak += 1
        cursor -= timedelta(days=1)

    return current_streak, best


current_streak, longest_streak = calculate_streaks(days, end)

language_sizes = {}
for repository in user["repositories"]["nodes"]:
    for edge in repository["languages"]["edges"]:
        language = edge["node"]["name"]
        language_sizes[language] = language_sizes.get(language, 0) + edge["size"]

languages = sorted(language_sizes.items(), key=lambda item: item[1], reverse=True)[:6]
# Percentages use all measured language bytes, not only the six displayed rows.
language_total = max(sum(language_sizes.values()), 1)

repositories = user["repositories"]["totalCount"]
followers = user["followers"]["totalCount"]
following = user["following"]["totalCount"]
contribution_total = calendar["totalContributions"]
commits = contributions["totalCommitContributions"]
pull_requests = contributions["totalPullRequestContributions"]
issues = contributions["totalIssueContributions"]
reviews = contributions["totalPullRequestReviewContributions"]


def svg_open(title, width=920, height=290):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
<defs>
  <linearGradient id="canvas" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0c1020"/>
    <stop offset="55%" stop-color="#17152b"/>
    <stop offset="100%" stop-color="#101a2b"/>
  </linearGradient>
  <linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#ef93c4"/>
    <stop offset="52%" stop-color="#a58cff"/>
    <stop offset="100%" stop-color="#63d9ff"/>
  </linearGradient>
  <linearGradient id="pink" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#ff72c6"/>
    <stop offset="100%" stop-color="#b28cff"/>
  </linearGradient>
  <filter id="softGlow" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse">
    <path d="M 34 0 L 0 0 0 34" fill="none" stroke="#8190b8" stroke-opacity=".08" stroke-width="1"/>
  </pattern>
</defs>
<rect width="100%" height="100%" rx="20" fill="url(#canvas)"/>
<rect width="100%" height="100%" rx="20" fill="url(#grid)"/>
<circle cx="{width - 55}" cy="5" r="116" fill="#a56dff" opacity=".08"/>
<path d="M0 58 H{width}" stroke="#ef93c4" stroke-opacity=".24"/>
<text x="30" y="38" fill="#f5c5e3" font-family="Segoe UI,Arial,sans-serif" font-size="20" font-weight="700">{escape(title)}</text>
<text x="{width - 30}" y="37" text-anchor="end" fill="#93a1c4" font-family="Consolas,monospace" font-size="10" letter-spacing="2">MR.CHEEKU // SYSTEM 3050</text>
<path d="M30 58 H{width - 30}" stroke="url(#neon)" stroke-width="2" opacity=".7"/>
"""


def svg_close():
    return "</svg>"


def text_node(x, y, value, size=16, color="#d8deef", weight="400", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
        f'font-family="Segoe UI,Arial,sans-serif" font-size="{size}" '
        f'font-weight="{weight}">{escape(str(value))}</text>'
    )


def metric_card(x, y, width, height, value, label):
    return f"""<g>
<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="13" fill="#151b2b" stroke="#3a3c58" stroke-width="1"/>
<rect x="{x}" y="{y}" width="4" height="{height}" rx="2" fill="url(#neon)"/>
<text x="{x + 18}" y="{y + 39}" fill="#fff4fc" font-family="Segoe UI,Arial,sans-serif" font-size="27" font-weight="700" filter="url(#softGlow)">{escape(str(value))}</text>
<text x="{x + 18}" y="{y + 64}" fill="#9da9c5" font-family="Segoe UI,Arial,sans-serif" font-size="12" letter-spacing=".4">{escape(str(label))}</text>
</g>"""


# Main profile statistics
svg = svg_open("Developer Telemetry", 920, 285)
top_cards = [
    (25, 76, 205, 82, commits, "Commits · 1 year"),
    (254, 76, 205, 82, pull_requests, "Pull requests"),
    (483, 76, 205, 82, issues, "Issues opened"),
    (712, 76, 183, 82, reviews, "Reviews"),
]
for item in top_cards:
    svg += metric_card(*item)

bottom_cards = [
    (140, 177, 205, 82, repositories, "Public repositories"),
    (358, 177, 205, 82, followers, "Followers"),
    (576, 177, 205, 82, following, "Following"),
]
for item in bottom_cards:
    svg += metric_card(*item)

svg += svg_close()
with open(f"{OUT}/github-stats.svg", "w", encoding="utf-8") as file:
    file.write(svg)


# Contribution streak
svg = svg_open("Contribution Streak", 920, 235)
svg += metric_card(38, 82, 260, 105, current_streak, "Current streak · days")
svg += metric_card(330, 82, 260, 105, longest_streak, "Longest streak · days")
svg += metric_card(622, 82, 260, 105, contribution_total, "Contributions · 1 year")
svg += text_node(460, 218, "Calculated from the public GitHub contribution calendar", 11, "#8795b6", "400", "middle")
svg += svg_close()
with open(f"{OUT}/github-streak.svg", "w", encoding="utf-8") as file:
    file.write(svg)


# Language distribution
svg = svg_open("Most Used Languages", 920, 290)
bar_y = 91
bar_width = 500
for language, byte_count in languages:
    percentage = byte_count / language_total * 100
    label = f"{language}  ·  {percentage:.1f}%"
    svg += text_node(38, bar_y, label, 13, "#d8deef", "600")
    svg += f'<rect x="270" y="{bar_y - 13}" width="{bar_width}" height="13" rx="6.5" fill="#242a40"/>'
    svg += f'<rect x="270" y="{bar_y - 13}" width="{max(3, bar_width * percentage / 100):.1f}" height="13" rx="6.5" fill="url(#neon)"/>'
    bar_y += 29
svg += text_node(460, 270, "Based on language bytes in up to 100 recently updated non-fork repositories", 10, "#8795b6", "400", "middle")
svg += svg_close()
with open(f"{OUT}/github-languages.svg", "w", encoding="utf-8") as file:
    file.write(svg)


# Milestones
svg = svg_open("Milestones & Achievements", 920, 260)
milestones = [
    (28, 82, 198, 92, "✦", "Contributions", contribution_total),
    (254, 82, 198, 92, "⌘", "Repositories", repositories),
    (480, 82, 198, 92, "◎", "Followers", followers),
    (706, 82, 186, 92, "↗", "Best streak", longest_streak),
]
for x, y, width, height, symbol, label, value in milestones:
    svg += f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="13" fill="#151b2b" stroke="#3a3c58"/>'
    svg += text_node(x + 17, y + 30, symbol, 20, "#ef93c4", "700")
    svg += text_node(x + 17, y + 61, value, 23, "#fff4fc", "700")
    svg += text_node(x + 17, y + 81, label, 11, "#9da9c5")
svg += text_node(460, 220, "Public profile activity · refreshed by GitHub Actions", 11, "#8795b6", "400", "middle")
svg += svg_close()
with open(f"{OUT}/github-trophies.svg", "w", encoding="utf-8") as file:
    file.write(svg)


# Daily contribution activity
svg = svg_open("Contribution Activity · Last 12 Months", 920, 315)
max_contributions = max((item["contributionCount"] for item in days), default=1) or 1
step = 850 / max(1, len(days))
x_position = 35
baseline = 252

for item in days:
    count = item["contributionCount"]
    if count == 0:
        bar_height = 3
        fill = "#252b40"
    else:
        bar_height = 5 + 130 * (count / max_contributions)
        if count / max_contributions > 0.72:
            fill = "#63d9ff"
        elif count / max_contributions > 0.42:
            fill = "#a58cff"
        else:
            fill = "#ef93c4"
    svg += (
        f'<rect x="{x_position:.2f}" y="{baseline - bar_height:.1f}" '
        f'width="{max(1.1, step - 0.55):.2f}" height="{bar_height:.1f}" '
        f'rx="1.4" fill="{fill}" opacity=".92"/>'
    )
    x_position += step

svg += f'<line x1="35" y1="{baseline}" x2="885" y2="{baseline}" stroke="#59617d" stroke-opacity=".6"/>'

# Place labels at the first day of each month represented in the calendar.
labelled_months = set()
for index, item in enumerate(days):
    day = date.fromisoformat(item["date"])
    month_key = (day.year, day.month)
    if day.day == 1 and month_key not in labelled_months:
        label_x = 35 + index * step
        svg += text_node(round(label_x, 1), 279, day.strftime("%b"), 10, "#93a1c4")
        labelled_months.add(month_key)

svg += text_node(460, 303, "Daily contributions · public GitHub contribution calendar", 10, "#8795b6", "400", "middle")
svg += svg_close()
with open(f"{OUT}/github-activity.svg", "w", encoding="utf-8") as file:
    file.write(svg)

print(
    "Generated profile assets: github-stats.svg, github-streak.svg, "
    "github-languages.svg, github-trophies.svg, github-activity.svg"
)
