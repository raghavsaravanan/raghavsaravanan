#!/usr/bin/env python3
"""
Fetch the last year of daily contributions (from the same public calendar the
profile page renders) plus public-repo stats, and write data/stats.json.

Standard library only, so the daily workflow needs no pip install. GITHUB_TOKEN
is optional and only raises the REST API rate limit.

    python scripts/fetch_stats.py
"""
import datetime
import json
import os
import re
import sys
import urllib.request

from theme import USER

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "stats.json")


def get(url, api=False):
    headers = {"User-Agent": f"{USER}-profile-readme"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
        body = resp.read().decode()
    return json.loads(body) if api else body


def fetch_days():
    page = get(f"https://github.com/users/{USER}/contributions")
    # Counts live in <tool-tip for="cell-id"> elements, not on the <td> cells.
    tips = {
        m.group(1): m.group(2)
        for m in re.finditer(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page)
    }
    days = []
    for cell in re.finditer(r"<td\b[^>]*ContributionCalendar-day[^>]*>", page):
        tag = cell.group(0)
        date = re.search(r'data-date="([\d-]+)"', tag)
        cell_id = re.search(r'\bid="([^"]+)"', tag)
        if not date:
            continue
        level = re.search(r'data-level="(\d)"', tag)
        count = re.match(r"(\d[\d,]*)", tips.get(cell_id.group(1), "") if cell_id else "")
        days.append({
            "date": date.group(1),
            "count": int(count.group(1).replace(",", "")) if count else 0,
            "level": int(level.group(1)) if level else 0,
        })
    if not days:
        sys.exit("no contribution cells found; GitHub's calendar markup may have changed")
    return sorted(days, key=lambda d: d["date"])


def streaks(days):
    longest = {"length": 0, "start": None, "end": None}
    run_start = None
    for i, day in enumerate(days):
        if day["count"]:
            run_start = i if run_start is None else run_start
            if i - run_start + 1 > longest["length"]:
                longest = {"length": i - run_start + 1, "start": days[run_start]["date"], "end": day["date"]}
        else:
            run_start = None

    # Today isn't over yet, so an empty today doesn't break the current streak.
    end = len(days) - 1 if days[-1]["count"] else len(days) - 2
    start = end
    while start >= 0 and days[start]["count"]:
        start -= 1
    length = end - start
    current = {"length": length, "start": days[start + 1]["date"] if length else None,
               "end": days[end]["date"] if length else None}
    return current, longest


def repo_stats():
    repos = get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner", api=True)
    public = [r for r in repos if not r["private"] and r["name"] != USER]
    languages = {}
    for repo in public:
        for lang, size in get(repo["languages_url"], api=True).items():
            languages[lang] = languages.get(lang, 0) + size
    total = sum(languages.values()) or 1
    top = sorted(languages.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {
        "public_repos": len(public),
        "original_repos": sum(1 for r in public if not r["fork"]),
        "stars": sum(r["stargazers_count"] for r in public),
        "languages": [{"name": name, "share": round(size / total, 4)} for name, size in top],
    }


def main():
    days = fetch_days()
    current, longest = streaks(days)
    active = [d for d in days if d["count"]]
    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"])

    monthly = {}
    for day in days:
        monthly[day["date"][:7]] = monthly.get(day["date"][:7], 0) + day["count"]
    # The calendar spans 53 weeks, so the first month is usually a sliver; keep the last 12.
    monthly = [{"month": k, "total": v} for k, v in sorted(monthly.items())][-12:]

    data = {
        "user": USER,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "active_days": len(active),
        "avg_per_active_day": round(total / len(active), 1) if active else 0,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly,
        "repos": repo_stats(),
        "days": days,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT}: {total} contributions, {len(active)} active days, "
          f"current streak {current['length']}, longest {longest['length']}")


if __name__ == "__main__":
    main()
