#!/usr/bin/env python3
"""Records this repository's GitHub traffic and draws it as an SVG chart.

GitHub only exposes 14 days of traffic, and only to someone with admin access, so a
scheduled workflow is the only thing that can both see the numbers and remember them.
Each run appends today's counts to `traffic/history.json` (which does persist) and
re-renders `traffic/views.svg`, so the README can show a chart that outlives the
14-day window.

Environment:
  GITHUB_REPOSITORY  owner/name (set by Actions)
  TRAFFIC_TOKEN      token with admin on the repository
                     (the default GITHUB_TOKEN cannot read traffic on public repos)
  TRAFFIC_DAYS       how many days to plot (default 30)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("TRAFFIC_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
DAYS = int(os.environ.get("TRAFFIC_DAYS", "30"))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HISTORY = os.path.join(ROOT, "traffic", "history.json")
CHART = os.path.join(ROOT, "traffic", "views.svg")

GREEN = "#2da44e"
PURPLE = "#8250df"
# Readmes embed this through <img>, where {INK} resolves to black, so the
# chart carries its own light card and ink colour to stay legible in dark mode.
CARD = "#ffffff"
INK = "#24292f"


def get(path: str) -> dict:
    req = urllib.request.Request(
        API + path,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "User-Agent": "traffic-chart",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        if exc.code == 403:
            # "Resource not accessible by integration": the workflow token is not an
            # admin on this repo, so it cannot see traffic at all. Not an error worth a
            # red X every morning — say so and leave the recorded history untouched.
            print(
                f"GET {path} -> 403: {body}\n"
                "Traffic needs admin rights. Add a repository secret TRAFFIC_TOKEN "
                "(a PAT with the repo's Administration: read permission) to record it.",
                file=sys.stderr,
            )
            raise SystemExit(0)
        raise SystemExit(f"GET {path} -> {exc.code}: {body}")


def load() -> dict:
    if not os.path.exists(HISTORY):
        return {"views": {}, "clones": {}}
    with open(HISTORY) as handle:
        return json.load(handle)


def record(history: dict, key: str, payload: dict) -> None:
    """Merges one API response into the stored history.

    Every run re-reports the whole 14-day window, so most of these are no-ops.
    Overwriting is deliberate: GitHub revises its own counts slightly, and the freshest
    observation of a given day is the best one available.
    """
    series = history.setdefault(key, {})
    for entry in payload.get(key, []):
        day = entry["timestamp"][:10]
        series[day] = {"count": entry["count"], "uniques": entry["uniques"]}


def nice_max(value: int) -> int:
    """Rounds up to 1/2/2.5/5 x 10^n so the axis gets round gridlines."""
    if value <= 4:
        return max(value, 1)
    magnitude = 10 ** (len(str(value)) - 1)
    for factor in (1, 2, 2.5, 5, 10):
        candidate = int(magnitude * factor)
        if candidate >= value:
            return candidate
    return value


def smooth_path(points: list[tuple[float, float]]) -> str:
    """Catmull-Rom through the points, emitted as cubic Béziers."""
    if not points:
        return ""
    if len(points) == 1:
        return f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    path = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        path.append(f"C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(path)


def render(history: dict) -> str:
    views = history.get("views", {})
    clones = history.get("clones", {})

    # The window is capped by the first day ever recorded: drawing zeros to the left of
    # that would claim "nobody visited" for days we simply were not measuring.
    today = dt.date.today()
    first = min((dt.date.fromisoformat(d) for d in views), default=today)
    start = max(first, today - dt.timedelta(days=DAYS - 1))
    days = [(start + dt.timedelta(days=i)).isoformat()
            for i in range((today - start).days + 1)]

    width, height = 760, 210
    left, right, top, bottom = 44, 16, 34, 30
    plot_w = width - left - right
    plot_h = height - top - bottom

    peak = max([views.get(d, {}).get("count", 0) for d in days] + [1])
    y_max = nice_max(peak)
    last_index = max(len(days) - 1, 1)
    x_at = lambda i: left + plot_w * i / last_index
    y_at = lambda v: top + plot_h * (1 - v / y_max)

    def points_of(series: dict) -> list[tuple[float, float]]:
        return [(x_at(i), y_at(series.get(d, {}).get("count", 0))) for i, d in enumerate(days)]

    view_pts = points_of(views)
    clone_pts = points_of(clones)

    def area(pts: list[tuple[float, float]]) -> str:
        line = smooth_path(pts)
        if not line:
            return ""
        base = top + plot_h
        return (f"{line} L {pts[-1][0]:.1f} {base:.1f} "
                f"L {pts[0][0]:.1f} {base:.1f} Z")

    total_views = sum(views.get(d, {}).get("count", 0) for d in days)
    total_uniques = sum(views.get(d, {}).get("uniques", 0) for d in days)
    total_clones = sum(clones.get(d, {}).get("count", 0) for d in days)

    grid = []
    # A tiny maximum (a brand-new repo) would otherwise get fractional gridlines that
    # all round to the same label. Drop to one line per unit instead.
    ticks = min(4, y_max)
    for i in range(ticks + 1):
        value = y_max * i / ticks
        y = y_at(value)
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
            f'stroke="{INK}" stroke-opacity="{0.16 if i else 0.3}" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="10" '
            f'fill="{INK}" fill-opacity="0.55">{int(value)}</text>'
        )

    labels = []
    for i in range(len(days) - 1, -1, -7):
        labels.append(
            f'<text x="{x_at(i):.1f}" y="{top + plot_h + 18}" text-anchor="middle" '
            f'font-size="10" fill="{INK}" fill-opacity="0.55">{days[i][5:]}</text>'
        )

    span = f"{days[0][5:]} 至 {days[-1][5:]}"
    if total_views == 0 and total_clones == 0:
        # Nothing has been recorded yet. A flat line at zero reads as a broken chart,
        # so say plainly that there is nothing to draw.
        empty = (
            f'<text x="{left + plot_w / 2:.1f}" y="{top + plot_h / 2:.1f}" '
            f'text-anchor="middle" font-size="13" fill="{INK}" fill-opacity="0.45">'
            f"还没有访问记录</text>"
        )
        series = ""
        legend = ""
    else:
        empty = ""
        series = (
            f'<path d="{area(view_pts)}" fill="url(#fill)"/>\n'
            f'    <path d="{smooth_path(clone_pts)}" fill="none" stroke="{PURPLE}" stroke-width="1.5"\n'
            f'          stroke-linecap="round" stroke-opacity="0.8" stroke-dasharray="4 3"/>\n'
            f'    <path d="{smooth_path(view_pts)}" fill="none" stroke="{GREEN}" stroke-width="2.2"\n'
            f'          stroke-linecap="round" stroke-linejoin="round"/>\n'
            f'    <circle cx="{view_pts[-1][0]:.1f}" cy="{view_pts[-1][1]:.1f}" r="3.2" fill="{GREEN}"/>'
        )
        legend = (
            f'<g transform="translate({left + 8},{top + plot_h - 10})" font-size="10" '
            f'fill="{INK}" fill-opacity="0.7">\n'
            f'      <line x1="0" y1="-3" x2="16" y2="-3" stroke="{GREEN}" stroke-width="2.2"/>\n'
            f'      <text x="22" y="0">浏览</text>\n'
            f'      <line x1="58" y1="-3" x2="74" y2="-3" stroke="{PURPLE}" stroke-width="1.5" stroke-dasharray="4 3"/>\n'
            f'      <text x="80" y="0">克隆</text>\n'
            f'    </g>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Repository traffic, {span}">
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{GREEN}" stop-opacity="0.32"/>
      <stop offset="100%" stop-color="{GREEN}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif">
    <rect x="0" y="0" width="{width}" height="{height}" rx="6" fill="{CARD}"/>
    <text x="{left}" y="18" font-size="12" fill="{INK}" fill-opacity="0.75">访问量 · {span}</text>
    <text x="{left + plot_w}" y="18" text-anchor="end" font-size="11" fill="{INK}" fill-opacity="0.55">浏览 {total_views} · 访客 {total_uniques} · 克隆 {total_clones}</text>
    {''.join(grid)}
    {empty}
    {series}
    <line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"
          stroke="{INK}" stroke-opacity="0.3" stroke-width="1"/>
    {''.join(labels)}
    {legend}
  </g>
</svg>
"""


def main() -> int:
    if not REPO or "/" not in REPO:
        raise SystemExit("GITHUB_REPOSITORY is not set to owner/name")
    if not TOKEN:
        print("TRAFFIC_TOKEN is not set; nothing to record.", file=sys.stderr)
        return 0

    history = load()
    record(history, "views", get(f"/repos/{REPO}/traffic/views?per=day"))
    record(history, "clones", get(f"/repos/{REPO}/traffic/clones?per=day"))
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "w") as handle:
        json.dump(history, handle, indent=1, sort_keys=True)
        handle.write("\n")
    with open(CHART, "w") as handle:
        handle.write(render(history))

    recorded = len(history.get("views", {}))
    total = sum(v["count"] for v in history.get("views", {}).values())
    print(f"{REPO}: {recorded} days recorded, {total} views total -> {CHART}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
