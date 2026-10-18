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
# Latin renders in Quickpen, CJK in Chen Weixun's hard-pen running script.
# Neither subset covers a glyph only the other has, so the browser's own
# fallback ordering does the split: it takes the first family that has it.
FONT = "'Segoe Print', 'Noto Sans', sans-serif"

THEMES = {
    "light": {"bg": "#ffffff", "ink": "#111111"},
    "dark": {"bg": "#0d1117", "ink": "#e6edf3"},
}

WINDOW_DAYS = 365

QUICKPEN_B64 = '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'   # Latin + digits only; no CJK glyphs.
CHEN_B64 = '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'       # CJK + digits; the Chinese face.

AVATAR_B64 = 'iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAB7UExURfDw8PLx8Orr7unr7u/v8Jqu2JKo1ZSp1pOp1pSq1uPm7PPy8Yqh04yj1Iuj1Iui0+Hl7PPz8Y6l1I2k1OLl7I6k1Nzh6pOo1tXb6OTn7eHk7O7u7/X08ezt74uj0/f18vHx8Onq7u7v8Ovs75it15Ko1tbc6Ymh0////+eL2U4AAAABYktHRCi9sLWyAAAAB3RJTUUH6goSBQAs/7i7+QAAAVhJREFUSMe9VGF3gjAMBOwEyipQ0E2nE+fc/v8/XKGkjKaxfezN+5YXjraX3EXRQxAHwhCSVRjY+P/kaZ0GIMt5MVDi1fpZbPwoRVWPhFTIxgvZyNYQNv7ve8pfCAFX+k3IypDvRWMIuZA9ttDaSldtTogYr9q2rfjuRej+6/6Aa4U3mHRRKxTHU/qu77o/F7hWMKvBBnSXUS15KD4cNWP2CoK8413tGu/sEsIwD1n1S8Y6WBmaoOchGn7s4rirr2k50x8T9DwauTtd1PZfeSrm+tsw8/i8aQd82frbgHncvpU/RCmQ/ugImEf/WEnq75PXnyH/QJjnDiaQucQIQuLOJcgdtFNW3+QS5A5ewnkfcklSW2r3vWuN3rSI4PYB4QvaB4QvaB9QvnD74J4vnD645wu3D7y+eGQuTYTAXAJCFppLQMiDcmnS264xtNqT3naNjxhB1YvwA2hBUsSnlXFOAAAAJXRFWHRkYXRlOmNyZWF0ZQAyMDI2LTEwLTE4VDA1OjAwOjQ0KzAwOjAwgpXKwgAAACV0RVh0ZGF0ZTptb2RpZnkAMjAyNi0xMC0xOFQwNTowMDo0NCswMDowMPPIcn4AAAAodEVYdGRhdGU6dGltZXN0YW1wADIwMjYtMTAtMThUMDU6MDA6NDQrMDA6MDCk3VOhAAAAAElFTkSuQmCC'


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

    # The x-axis only spans the stretch of history that actually moves. A repository
    # that sat at zero for five months before its first star should not spend five
    # months of width drawing that flat line.
    def change_days(points: list[tuple[str, int]]) -> list[str]:
        out, previous = [], None
        for day, value in points:
            if previous is None or value != previous:
                out.append(day)
            previous = value
        return out

    active = sorted(set(change_days(view_cum)) | set(change_days(dl_points))
                    | set(change_days(st_points)))
    if active:
        start = dt.date.fromisoformat(active[-1])
        for day in reversed(active[:-1]):
            candidate = dt.date.fromisoformat(day)
            if (start - candidate).days > 45:
                break
            start = candidate
    else:
        start = today - dt.timedelta(days=6)
    start = min(start, today - dt.timedelta(days=6))          # at least a week wide
    start = max(start, today - dt.timedelta(days=WINDOW_DAYS - 1))
    days = [(start + dt.timedelta(days=i)).isoformat()
            for i in range((today - start).days + 1)]

    width, height = 800, 533
    left, right, top, bottom = 96, 48, 96, 92
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
    legend_items = []
    cursor = 0.0
    for label, color, points, total in series:
        pts = series_points(points, axis_max)
        if pts:
            paths.append(
                f'<path d="{smooth_path(pts, top, top + plot_h)}" fill="none" '
                f'stroke="{color}" stroke-width="3" stroke-linecap="round" '
                f'stroke-linejoin="round" filter="url(#wobble)"/>'
            )
        text = f"{label} {total}"
        legend_items.append(
            f'<line x1="{cursor:.0f}" y1="-5" x2="{cursor + 18:.0f}" y2="-5" '
            f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
            f'<text x="{cursor + 24:.0f}" y="0">{text}</text>'
        )
        # Rough advance: 18px swatch + 6px gap + one em per CJK char, half per Latin.
        cursor += 24 + sum(18 if ord(ch) > 0x2E80 else 9 for ch in text) + 22

    legend = (
        f'<g transform="translate({left + 14},{top + 22})" font-size="18" fill="{ink}">'
        f'<rect x="-10" y="-20" width="{cursor - 8:.0f}" height="30" rx="7" fill="{bg}" '
        f'fill-opacity="0.92" stroke="{ink}" stroke-width="2" '
        f'filter="url(#wobble)"/>'
        f'{"".join(legend_items)}</g>'
    )

    # Title: the owner's avatar in a circle, then "History".
    avatar_cx, avatar_cy, avatar_r = 344, 46, 18
    title_x = avatar_cx + avatar_r + 12

    # Quickpen is Latin-only, so CJK falls through to Chen's face automatically.
    font_face = (
        "<style>"
        "@font-face{font-family:Quickpen;"
        f"src:url(data:font/woff2;base64,{QUICKPEN_B64}) format('woff2');}}"
        "@font-face{font-family:ChenYX;"
        f"src:url(data:font/woff2;base64,{CHEN_B64}) format('woff2');}}"
        "</style>"
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="History">
  <defs>
    {font_face}
    <clipPath id="avatarClip"><circle cx="{avatar_cx}" cy="{avatar_cy}" r="{avatar_r}"/></clipPath>
    <filter id="wobble" x="-15%" y="-15%" width="130%" height="130%">
      <feTurbulence baseFrequency=".05" result="noise" type="fractalNoise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="4"
                         xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <rect width="{width}" height="{height}" fill="{bg}"/>
  <g font-family="Quickpen, ChenYX, {FONT}">
    <image href="data:image/png;base64,{AVATAR_B64}" x="{avatar_cx - avatar_r}"
           y="{avatar_cy - avatar_r}" width="{avatar_r * 2}" height="{avatar_r * 2}"
           clip-path="url(#avatarClip)"/>
    <text x="{title_x}" y="{avatar_cy + 12}" font-size="34" fill="{ink}">History</text>
    {''.join(y_ticks)}
    {axes}
    {''.join(x_ticks)}
    <text x="{left + plot_w / 2:.0f}" y="{top + plot_h + 66}" text-anchor="middle"
          font-size="20" fill="{ink}" fill-opacity="0.75">date</text>
    <text x="38" y="{top + plot_h / 2:.0f}" text-anchor="middle" font-size="20"
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
