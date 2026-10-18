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
    first_days = [dt.date.fromisoformat(d) for d in list(downloads) + list(stars)]
    start = min(first_days) if first_days else today
    start = max(start, today - dt.timedelta(days=WINDOW_DAYS - 1))
    days = [(start + dt.timedelta(days=i)).isoformat()
            for i in range((today - start).days + 1)]

    width, height = 800, 533
    left, right, top, bottom = 84, 84, 146, 88
    plot_w = width - left - right
    plot_h = height - top - bottom

    # Downloads only exist from the first day the recorder ran; stars are backfilled,
    # so their series is longer and starts earlier.
    dl_days = sorted(downloads)
    dl_points = [(d, downloads[d]) for d in dl_days]
    st_points = [(d, stars[d]) for d in days if d in stars]

    draw_dl = len(dl_points) >= 2 and dl_points[-1][1] > 0
    draw_st = len(st_points) >= 2 and st_points[-1][1] > 0
    dual = draw_dl and draw_st

    def value_at(series: list[tuple[str, int]], day: str) -> int:
        """Cumulative value on `day`, carrying the last known one forward."""
        value = 0
        for d, v in series:
            if d > day:
                break
            value = v
        return value

    last_index = max(len(days) - 1, 1)
    x_at = lambda i: left + plot_w * i / last_index

    # Downloads are only known from the first day the recorder ran. Days before that
    # are unknown, not zero, so the line starts there instead of at the window edge.
    dl_first = dl_days[0] if dl_days else days[0]
    dl_index = [(i, d) for i, d in enumerate(days) if d >= dl_first]
    st_index = list(enumerate(days))

    dl_max = nice_max(max((v for _, v in dl_points), default=0)) if draw_dl else 1
    st_max = nice_max(max((v for _, v in st_points), default=0)) if draw_st else 1
    axis_max = dl_max if dual else (dl_max if draw_dl else st_max)

    def y_at(value: float, top_value: int) -> float:
        return top + plot_h * (1 - value / top_value)

    dl_pts = [(x_at(i), min(max(y_at(value_at(dl_points, d), dl_max), top), top + plot_h))
              for i, d in dl_index] if draw_dl else []
    st_pts = [(x_at(i), min(max(y_at(value_at(st_points, d), st_max), top), top + plot_h))
              for i, d in st_index] if draw_st else []

    ticks = min(5, axis_max)
    y_ticks = []
    for i in range(ticks + 1):
        value = axis_max * i / ticks
        y = y_at(value, axis_max)
        y_ticks.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
            f'stroke="{ink}" stroke-opacity="{0.12 if i else 0.28}" stroke-width="1.4" '
            f'filter="url(#wobble)"/>'
            f'<text x="{left - 14}" y="{y + 6:.1f}" text-anchor="end" font-size="17" '
            f'fill="{ink}" fill-opacity="0.8">{int(value)}</text>'
        )


    if dual:
        st_ticks = min(5, st_max)
        for i in range(st_ticks + 1):
            value = st_max * i / st_ticks
            y = y_at(value, st_max)
            y_ticks.append(
                f'<text x="{left + plot_w + 14}" y="{y + 6:.1f}" text-anchor="start" '
                f'font-size="17" fill="{STARS}" fill-opacity="0.85">{int(value)}</text>'
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
    recent_views = sum(v["count"] for d, v in views.items()
                       if d >= (today - dt.timedelta(days=13)).isoformat())
    total_dl = dl_points[-1][1] if dl_points else 0
    total_st = st_points[-1][1] if st_points else 0

    # The numbers always show, even on day one when there is only a single point and
    # therefore no line to draw yet.
    legend_parts = []
    x_cursor = width / 2 - 130
    if total_dl:
        swatch = (
            f'<line x1="{x_cursor:.0f}" y1="100" x2="{x_cursor + 26:.0f}" y2="100" '
            f'stroke="{DOWNLOADS}" stroke-width="3" stroke-linecap="round" '
            f'filter="url(#wobble)"/>' if draw_dl else ""
        )
        legend_parts.append(
            f'{swatch}<text x="{x_cursor + (36 if draw_dl else 0):.0f}" y="106">'
            f'下载 {total_dl}</text>'
        )
        x_cursor += 118
    if total_st:
        swatch = (
            f'<line x1="{x_cursor:.0f}" y1="100" x2="{x_cursor + 26:.0f}" y2="100" '
            f'stroke="{STARS}" stroke-width="2.6" stroke-linecap="round" '
            f'filter="url(#wobble)"/>' if draw_st else ""
        )
        legend_parts.append(
            f'{swatch}<text x="{x_cursor + (36 if draw_st else 0):.0f}" y="106">'
            f'Star {total_st}</text>'
        )
    legend = f'<g font-size="18" fill="{ink}">{"".join(legend_parts)}</g>'

    left_label = "下载" if draw_dl else ("Star" if draw_st else "累计")
    # Downloads have no backfill: the curve can only start on the first day the
    # recorder ran. Say so instead of letting a lone number sit above a 0-3 axis.
    note = ""
    if dl_points and not draw_dl:
        note = (f'<text x="{width / 2:.0f}" y="128" text-anchor="middle" font-size="15" '
                f'fill="{ink}" fill-opacity="0.5">下载量从 {dl_days[0][5:]} 开始记录，'
                f'明天起会有曲线</text>')

    parts = []
    if draw_st:
        parts.append(
            f'<path d="{smooth_path(st_pts, top, top + plot_h)}" fill="none" '
            f'stroke="{STARS}" stroke-width="2.6" stroke-linecap="round" '
            f'stroke-linejoin="round" filter="url(#wobble)"/>'
        )
    if draw_dl:
        parts.append(
            f'<path d="{smooth_path(dl_pts, top, top + plot_h)}" fill="none" '
            f'stroke="{DOWNLOADS}" stroke-width="3" stroke-linecap="round" '
            f'stroke-linejoin="round" filter="url(#wobble)"/>'
        )
    if not parts:
        parts.append(
            f'<text x="{left + plot_w / 2:.1f}" y="{top + plot_h / 2:.1f}" '
            f'text-anchor="middle" font-size="22" fill="{ink}" fill-opacity="0.45">'
            f"记录才刚开始，明天这里会长出曲线</text>"
        )
    body = "".join(parts)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="使用趋势 {span}">
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
          fill="{ink}">使用趋势</text>
    <text x="{width / 2:.0f}" y="72" text-anchor="middle" font-size="17"
          fill="{ink}" fill-opacity="0.65">{REPO or "仓库"} · {span}</text>
    {legend}
    {note}
    {''.join(y_ticks)}
    {axes}
    {''.join(x_ticks)}
    <text x="{left + plot_w / 2:.0f}" y="{top + plot_h + 54}" text-anchor="middle"
          font-size="18" fill="{ink}" fill-opacity="0.75">日期</text>
    <text x="34" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-size="18"
          fill="{ink}" fill-opacity="0.75"
          transform="rotate(-90 34 {top + plot_h / 2:.0f})">{left_label}</text>
    {body}
    <text x="{width / 2:.0f}" y="{height - 10}" text-anchor="middle" font-size="15"
          fill="{ink}" fill-opacity="0.5">近 14 天浏览 {recent_views}</text>
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
