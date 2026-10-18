#!/usr/bin/env python3
"""Records this repository's GitHub traffic and draws it in a hand-drawn style.

GitHub only exposes 14 days of traffic, and only to someone with admin access, so a
scheduled workflow is the only thing that can both see the numbers and remember them.
Each run appends today's counts to `traffic/history.json` (which does persist) and
re-renders `traffic/views.svg` + `traffic/views-dark.svg`, so the README can show a
chart that outlives the 14-day window.

The look imitates the hand-drawn Star History chart: wobbly strokes from an
feTurbulence displacement filter, a handwriting font stack, and a light/dark pair so
`<picture>` can pick the right one. The font is *not* embedded — xkcd-script is
CC BY-NC, and these are redistributable repositories — so the stack falls back to
whatever handwriting face the reader's system has.

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
CHART_DARK = os.path.join(ROOT, "traffic", "views-dark.svg")

VIEWS = "#dd4528"    # the warm red Star History uses for its line
CLONES = "#3b7dd8"
FONT = ("xkcd, 'Comic Sans MS', 'Chalkboard SE', 'Bradley Hand', "
        "'Segoe Print', 'Noto Sans', sans-serif")

THEMES = {
    "light": {"bg": "#ffffff", "ink": "#111111"},
    "dark": {"bg": "#0d1117", "ink": "#e6edf3"},
}


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


def smooth_path(points: list[tuple[float, float]],
                y_lo: float | None = None, y_hi: float | None = None) -> str:
    """Catmull-Rom through the points, emitted as cubic Béziers.

    `y_lo`/`y_hi` clamp the control points, not just the data points: the spline
    overshoots around sharp minima, and an unclamped curve dips visibly below zero.
    """
    if not points:
        return ""
    if len(points) == 1:
        return f"M {points[0][0]:.1f} {points[0][1]:.1f}"

    def clamp(y: float) -> float:
        if y_lo is not None:
            y = max(y, y_lo)
        if y_hi is not None:
            y = min(y, y_hi)
        return y

    path = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, clamp(p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, clamp(p2[1] - (p3[1] - p1[1]) / 6))
        path.append(f"C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(path)


def render(history: dict, theme: str = "light") -> str:
    colors = THEMES[theme]
    bg, ink = colors["bg"], colors["ink"]
    views = history.get("views", {})
    clones = history.get("clones", {})

    # The window is capped by the first day ever recorded: drawing zeros to the left of
    # that would claim "nobody visited" for days we simply were not measuring.
    today = dt.date.today()
    first = min((dt.date.fromisoformat(d) for d in views), default=today)
    start = max(first, today - dt.timedelta(days=DAYS - 1))
    days = [(start + dt.timedelta(days=i)).isoformat()
            for i in range((today - start).days + 1)]

    width, height = 800, 533
    left, right, top, bottom = 78, 44, 104, 84
    plot_w = width - left - right
    plot_h = height - top - bottom

    peak = max([views.get(d, {}).get("count", 0) for d in days]
               + [clones.get(d, {}).get("count", 0) for d in days] + [1])
    y_max = nice_max(peak)
    last_index = max(len(days) - 1, 1)
    x_at = lambda i: left + plot_w * i / last_index
    y_at = lambda v: top + plot_h * (1 - v / y_max)

    def points_of(series: dict) -> list[tuple[float, float]]:
        # Clamp to the plot area: Catmull-Rom overshoots at sharp local minima, and a
        # dip below the baseline would read as negative traffic.
        return [(x_at(i), min(max(y_at(series.get(d, {}).get("count", 0)), top),
                              top + plot_h))
                for i, d in enumerate(days)]

    view_pts = points_of(views)
    clone_pts = points_of(clones)

    total_views = sum(views.get(d, {}).get("count", 0) for d in days)
    total_uniques = sum(views.get(d, {}).get("uniques", 0) for d in days)
    total_clones = sum(clones.get(d, {}).get("count", 0) for d in days)

    ticks = min(5, y_max)
    y_ticks = []
    for i in range(ticks + 1):
        value = y_max * i / ticks
        y = y_at(value)
        y_ticks.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
            f'stroke="{ink}" stroke-opacity="{0.12 if i else 0.28}" stroke-width="1.4" '
            f'filter="url(#wobble)"/>'
            f'<text x="{left - 14}" y="{y + 6:.1f}" text-anchor="end" font-size="17" '
            f'fill="{ink}" fill-opacity="0.8">{int(value)}</text>'
        )

    x_ticks = []
    step = max(1, round(len(days) / 6))
    for i in range(0, len(days), step):
        anchor = "start" if i == 0 else "end" if i + step >= len(days) else "middle"
        x_ticks.append(
            f'<text x="{x_at(i):.1f}" y="{top + plot_h + 28}" text-anchor="{anchor}" '
            f'font-size="17" fill="{ink}" fill-opacity="0.8">{days[i][5:]}</text>'
        )

    axes = (
        f'<path d="M {left} {top} L {left} {top + plot_h} L {left + plot_w} {top + plot_h}" '
        f'fill="none" stroke="{ink}" stroke-width="2.6" stroke-linecap="round" '
        f'filter="url(#wobble)"/>'
    )

    span = f"{days[0][5:]} 至 {days[-1][5:]}"
    if total_views == 0 and total_clones == 0:
        body = (
            f'<text x="{left + plot_w / 2:.1f}" y="{top + plot_h / 2:.1f}" '
            f'text-anchor="middle" font-size="24" fill="{ink}" fill-opacity="0.45">'
            f"还没有访问记录</text>"
        )
        legend = ""
    else:
        body = (
            f'<path d="{smooth_path(clone_pts, top, top + plot_h)}" fill="none" stroke="{CLONES}" '
            f'stroke-width="2.4" stroke-opacity="0.85" stroke-dasharray="7 6" '
            f'stroke-linecap="round" filter="url(#wobble)"/>'
            f'<path d="{smooth_path(view_pts, top, top + plot_h)}" fill="none" stroke="{VIEWS}" '
            f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
            f'filter="url(#wobble)"/>'
            f'<circle cx="{view_pts[-1][0]:.1f}" cy="{view_pts[-1][1]:.1f}" r="5" '
            f'fill="{VIEWS}" stroke="{bg}" stroke-width="2"/>'
        )
        legend = (
            f'<g font-size="18" fill="{ink}">'
            f'<line x1="{width / 2 - 132:.0f}" y1="94" x2="{width / 2 - 106:.0f}" y2="94" '
            f'stroke="{VIEWS}" stroke-width="3" stroke-linecap="round" filter="url(#wobble)"/>'
            f'<text x="{width / 2 - 96:.0f}" y="100">浏览 {total_views}</text>'
            f'<line x1="{width / 2 + 14:.0f}" y1="94" x2="{width / 2 + 40:.0f}" y2="94" '
            f'stroke="{CLONES}" stroke-width="2.4" stroke-dasharray="7 6" '
            f'stroke-linecap="round" filter="url(#wobble)"/>'
            f'<text x="{width / 2 + 50:.0f}" y="100">克隆 {total_clones}</text>'
            f"</g>"
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="访问量 {span}">
  <defs>
    <filter id="wobble" width="100%" height="100%" x="-5" y="-5" filterUnits="userSpaceOnUse">
      <feTurbulence baseFrequency=".05" result="noise" type="fractalNoise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="4"
                         xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <rect width="{width}" height="{height}" fill="{bg}"/>
  <g font-family="{FONT}">
    <text x="{width / 2:.0f}" y="46" text-anchor="middle" font-size="30"
          fill="{ink}">访问量</text>
    <text x="{width / 2:.0f}" y="72" text-anchor="middle" font-size="17"
          fill="{ink}" fill-opacity="0.65">{REPO or "仓库"} · {span} · 访客 {total_uniques}</text>
    {''.join(y_ticks)}
    {axes}
    {''.join(x_ticks)}
    <text x="{left + plot_w / 2:.0f}" y="{top + plot_h + 64}" text-anchor="middle"
          font-size="18" fill="{ink}" fill-opacity="0.75">日期</text>
    <text x="34" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-size="18"
          fill="{ink}" fill-opacity="0.75"
          transform="rotate(-90 34 {top + plot_h / 2:.0f})">次数</text>
    {body}
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
        handle.write(render(history, "light"))
    with open(CHART_DARK, "w") as handle:
        handle.write(render(history, "dark"))

    recorded = len(history.get("views", {}))
    total = sum(v["count"] for v in history.get("views", {}).values())
    print(f"{REPO}: {recorded} days recorded, {total} views total -> {CHART}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
