#!/usr/bin/env python3
"""Records this repository's usage numbers and draws them in a hand-drawn style.

Two real signals go on the chart, both cumulative so they only ever go up:

  * **下载** — the sum of every Release asset's `download_count`. GitHub does not keep
    a history for this, so today's total is snapshotted into `traffic/history.json`
    once a day; the curve starts on the first day the recorder ran.
  * **Star** — the stargazers endpoint accepts `application/vnd.github.star+json`,
    which returns each star's exact `starred_at`. That is a full history, so this
    line is backfilled to the repository's creation date and is correct immediately.

Page views are kept as a one-line figure rather than a curve: GitHub only exposes
14 days of them, which is too short to draw a history against. Clone counts are not
recorded at all — on a repository that ships binaries they are almost entirely bots,
CI checkouts and mirroring services, not people.

The look imitates the hand-drawn Star History chart: wobbly strokes from an
feTurbulence displacement filter, a handwriting font stack, and a light/dark pair so
`<picture>` can pick the right one. The font is *not* embedded — xkcd-script is
CC BY-NC, and these are redistributable repositories — so the stack falls back to
whatever handwriting face the reader's system has.

Environment:
  GITHUB_REPOSITORY  owner/name (set by Actions)
  TRAFFIC_TOKEN      token with admin on the repository
                     (the default GITHUB_TOKEN cannot read traffic on public repos)
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HISTORY = os.path.join(ROOT, "traffic", "history.json")
CHART = os.path.join(ROOT, "traffic", "views.svg")
CHART_DARK = os.path.join(ROOT, "traffic", "views-dark.svg")

DOWNLOADS = "#dd4528"   # the warm red Star History uses for its line
STARS = "#3b7dd8"
VIEWS_COLOR = "#2da44e"
FONT = ("xkcd, 'Comic Sans MS', 'Chalkboard SE', 'Bradley Hand', "
        "'Segoe Print', 'Noto Sans', sans-serif")

THEMES = {
    "light": {"bg": "#ffffff", "ink": "#111111"},
    "dark": {"bg": "#0d1117", "ink": "#e6edf3"},
}

WINDOW_DAYS = 365


def request(path: str, accept: str = "application/vnd.github+json"):
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": accept,
        "User-Agent": "traffic-chart",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
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
        return {"views": {}, "downloads": {}, "stars": {}}
    with open(HISTORY) as handle:
        data = json.load(handle)
    for key in ("views", "downloads", "stars"):
        data.setdefault(key, {})
    data.pop("clones", None)
    return data


def record_views(history: dict, payload: dict) -> None:
    """Merges one API response into the stored history.

    Every run re-reports the whole 14-day window, so most of these are no-ops.
    Overwriting is deliberate: GitHub revises its own counts slightly, and the freshest
    observation of a given day is the best one available.
    """
    series = history.setdefault("views", {})
    for entry in payload.get("views", []):
        day = entry["timestamp"][:10]
        series[day] = {"count": entry["count"], "uniques": entry["uniques"]}


def total_downloads(repo: str) -> int:
    """Every asset of every release, minus the checksum files.

    `download_count` is cumulative per asset and never resets, so summing the releases
    gives the all-time total. SHA256SUMS files are excluded — downloading a checksum
    is not installing the thing.
    """
    releases = request(f"/repos/{repo}/releases?per_page=100") or []
    total = 0
    for release in releases:
        for asset in release.get("assets", []):
            if "SHA256SUMS" in asset.get("name", ""):
                continue
            total += asset.get("download_count", 0)
    return total


def star_history(repo: str, created: dt.date, today: dt.date) -> dict[str, int]:
    """Cumulative stars for every day since the repository was created.

    `starred_at` only comes back when the request asks for the `star+json` media type.
    """
    stars: list[str] = []
    page = 1
    while True:
        batch = request(
            f"/repos/{repo}/stargazers?per_page=100&page={page}",
            accept="application/vnd.github.star+json",
        ) or []
        stars.extend(entry["starred_at"][:10] for entry in batch if entry.get("starred_at"))
        if len(batch) < 100:
            break
        page += 1

    per_day: dict[str, int] = {}
    for day in stars:
        per_day[day] = per_day.get(day, 0) + 1

    series: dict[str, int] = {}
    total = 0
    cursor = created
    while cursor <= today:
        key = cursor.isoformat()
        total += per_day.get(key, 0)
        series[key] = total
        cursor += dt.timedelta(days=1)
    return series


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
    downloads = history.get("downloads", {})
    stars = history.get("stars", {})
    views = history.get("views", {})

    today = dt.date.today()

    # Views are daily counts; turn them into a running total so all three series
    # share the same "only ever goes up" shape as the reference chart.
    view_cum: list[tuple[str, int]] = []
    running = 0
    for day in sorted(views):
        running += views[day]["count"]
        view_cum.append((day, running))

    dl_points = [(d, downloads[d]) for d in sorted(downloads)]
    st_points = [(d, stars[d]) for d in sorted(stars)]

    firsts = [dt.date.fromisoformat(p[0][0]) for p in (view_cum, dl_points, st_points) if p]
    start = min(firsts) if firsts else today
    start = max(start, today - dt.timedelta(days=WINDOW_DAYS - 1))
    days = [(start + dt.timedelta(days=i)).isoformat()
            for i in range((today - start).days + 1)]

    width, height = 800, 533
    left, right, top, bottom = 96, 48, 96, 88
    plot_w = width - left - right
    plot_h = height - top - bottom
    last_index = max(len(days) - 1, 1)
    x_at = lambda i: left + plot_w * i / last_index

    def carry(points: list[tuple[str, int]], day: str) -> int:
        """Cumulative value on `day`, carrying the last known one forward."""
        value = 0
        for d, v in points:
            if d > day:
                break
            value = v
        return value

    def series_points(points: list[tuple[str, int]], top_value: int):
        """Only from the first recorded day: before that the value is unknown, not 0."""
        if len(points) < 2:
            return []
        first = points[0][0]
        return [(x_at(i), min(max(top + plot_h * (1 - carry(points, d) / top_value), top),
                              top + plot_h))
                for i, d in enumerate(days) if d >= first]

    totals = {
        "views": view_cum[-1][1] if view_cum else 0,
        "downloads": dl_points[-1][1] if dl_points else 0,
        "stars": st_points[-1][1] if st_points else 0,
    }
    peak = max(list(totals.values()) + [1])
    axis_max = nice_max(peak)
    ticks = min(5, axis_max)

    y_ticks = []
    for i in range(ticks + 1):
        value = axis_max * i / ticks
        y = top + plot_h * (1 - value / axis_max)
        y_ticks.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
            f'stroke="{ink}" stroke-opacity="{0.12 if i else 0.28}" stroke-width="1.4" '
            f'filter="url(#wobble)"/>'
            f'<text x="{left - 14}" y="{y + 6:.1f}" text-anchor="end" font-size="17" '
            f'fill="{ink}" fill-opacity="0.8">{int(value)}</text>'
        )

    # Long spans get month names, short ones keep the MM-DD ticks.
    x_ticks = []
    if len(days) > 70:
        seen = set()
        for i, d in enumerate(days):
            month = d[:7]
            if month in seen:
                continue
            seen.add(month)
            if i == 0 and len(days) - i < 7:
                continue
            x_ticks.append(
                f'<text x="{x_at(i):.1f}" y="{top + plot_h + 28}" text-anchor="middle" '
                f'font-size="17" fill="{ink}" fill-opacity="0.8">{int(d[5:7])} 月</text>'
            )
    else:
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

    series = [
        ("浏览", VIEWS_COLOR, view_cum, totals["views"]),
        ("下载", DOWNLOADS, dl_points, totals["downloads"]),
        ("Star", STARS, st_points, totals["stars"]),
    ]
    paths = []
    legend_rows = []
    for index, (label, color, points, total) in enumerate(series):
        pts = series_points(points, axis_max)
        if pts:
            paths.append(
                f'<path d="{smooth_path(pts, top, top + plot_h)}" fill="none" '
                f'stroke="{color}" stroke-width="3" stroke-linecap="round" '
                f'stroke-linejoin="round" filter="url(#wobble)"/>'
            )
        row_y = index * 30
        legend_rows.append(
            f'<line x1="0" y1="{row_y - 6}" x2="24" y2="{row_y - 6}" stroke="{color}" '
            f'stroke-width="3" stroke-linecap="round"/>'
            f'<text x="34" y="{row_y}">{label} {total}</text>'
        )

    legend = (
        f'<g transform="translate({left + 18},{top + 34})" font-size="18" fill="{ink}">'
        f'<rect x="-12" y="-30" width="196" height="104" rx="8" fill="{bg}" '
        f'fill-opacity="0.92" stroke="{ink}" stroke-width="2.2" '
        f'filter="url(#wobble)"/>'
        f'{"".join(legend_rows)}</g>'
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="使用趋势">
  <defs>
    <filter id="wobble" x="-15%" y="-15%" width="130%" height="130%">
      <feTurbulence baseFrequency=".05" result="noise" type="fractalNoise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="4"
                         xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <rect width="{width}" height="{height}" fill="{bg}"/>
  <g font-family="{FONT}">
    <text x="{width / 2:.0f}" y="46" text-anchor="middle" font-size="30"
          fill="{ink}">使用趋势</text>
    {''.join(y_ticks)}
    {axes}
    {''.join(x_ticks)}
    <text x="{left + plot_w / 2:.0f}" y="{top + plot_h + 66}" text-anchor="middle"
          font-size="18" fill="{ink}" fill-opacity="0.75">日期</text>
    <text x="38" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-size="18"
          fill="{ink}" fill-opacity="0.75"
          transform="rotate(-90 38 {top + plot_h / 2:.0f})">累计</text>
    {''.join(paths)}
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
    record_views(history, request(f"/repos/{REPO}/traffic/views?per=day") or {})

    today = dt.date.today()
    history["downloads"][today.isoformat()] = total_downloads(REPO)

    repo_info = request(f"/repos/{REPO}") or {}
    created = dt.date.fromisoformat(repo_info["created_at"][:10])
    history["stars"] = star_history(REPO, created, today)

    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "w") as handle:
        json.dump(history, handle, indent=1, sort_keys=True)
        handle.write("\n")
    with open(CHART, "w") as handle:
        handle.write(render(history, "light"))
    with open(CHART_DARK, "w") as handle:
        handle.write(render(history, "dark"))

    print(f"{REPO}: {len(history['downloads'])} download days, "
          f"{len(history['stars'])} star days, "
          f"{history['downloads'][today.isoformat()]} downloads total -> {CHART}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
