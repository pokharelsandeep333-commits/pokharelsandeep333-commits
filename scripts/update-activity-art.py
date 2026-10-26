"""Render a dated contribution skyline from GitHub's anonymous public calendar."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "activity"
ACCOUNT = "pokharelsandeep333-commits"
WEEKS = 24


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.tooltips = {}
        self.current_id = None
        self.parts = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "td" and "data-date" in attributes:
            self.cells[attributes["id"]] = {
                "date": attributes["data-date"],
                "level": int(attributes["data-level"]),
            }
        if tag == "tool-tip":
            self.current_id = attributes.get("for")
            self.parts = []

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.current_id:
            self.tooltips[self.current_id] = "".join(self.parts).strip()
            self.current_id = None

    def handle_data(self, value):
        if self.current_id:
            self.parts.append(value)

    def days(self):
        result = {}
        for cell_id, item in self.cells.items():
            tooltip = self.tooltips.get(cell_id, "")
            match = re.fullmatch(r"([\d,]+) contributions? on .+", tooltip)
            if match:
                count = int(match.group(1).replace(",", ""))
            elif tooltip.startswith("No contributions on "):
                count = 0
            else:
                raise ValueError(f"Unrecognized contribution tooltip for {item['date']}")
            if count < 0 or not 0 <= item["level"] <= 4:
                raise ValueError("Invalid contribution data")
            date.fromisoformat(item["date"])
            result[item["date"]] = {**item, "count": count}
        if not result:
            raise ValueError("The public calendar contained no day cells")
        return result


def calendar_url(year: int, through: date) -> str:
    end = min(through, date(year, 12, 31))
    query = urlencode({"from": f"{year}-01-01", "to": end.isoformat()})
    return f"https://github.com/users/{ACCOUNT}/contributions?{query}"


def collect_days(through: date, html_file: Path | None):
    first = through - timedelta(days=WEEKS * 7 - 1)
    available = {}
    sources = []
    for year in range(first.year, through.year + 1):
        url = calendar_url(year, through)
        sources.append(url)
        if html_file:
            content = html_file.read_text(encoding="utf-8")
        else:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 (GitHub profile artwork)"})
            with urlopen(request, timeout=25) as response:
                content = response.read().decode("utf-8")
        parser = CalendarParser()
        parser.feed(content)
        available.update(parser.days())
    days = []
    for offset in range(WEEKS * 7):
        day = (first + timedelta(days=offset)).isoformat()
        if day not in available:
            raise ValueError(f"Missing calendar day: {day}. No zero values were invented.")
        days.append(available[day])
    return first, days, sources


def short_date(day: date):
    return f"{day:%b} {day.day}"


def blend(hex_color: str, amount: float):
    values = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(value + (255 - value) * amount):02x}" for value in values)


def render(days, first: date, through: date, dark: bool, mobile: bool):
    width, height = (640, 410) if mobile else (1280, 340)
    bg = "#050e1f" if dark else "#F4F7FC"
    ink = "#e8edf5" if dark else "#002D62"
    muted = "#9AACCA" if dark else "#50627D"
    gold = "#FFC72C"
    rule = "#24446C" if dark else "#CDD8E8"
    total = sum(day["count"] for day in days)
    active = sum(day["count"] > 0 for day in days)
    peak = max(day["count"] for day in days)
    chart_x, chart_width, baseline = (28, 578, 330) if mobile else (338, 892, 263)
    chart_height = 146 if mobile else 158
    step = chart_width / len(days)
    bar_width = step * 0.64
    depth = step * 0.22
    palette = ["#142943" if dark else "#DDE6F1", "#2C5F94", "#4C8DC2", "#C5A336", gold]
    buildings = []
    months = []
    for index, day in enumerate(days):
        parsed = date.fromisoformat(day["date"])
        x = chart_x + index * step
        count = day["count"]
        bar_height = count / peak * chart_height if peak else 0
        color = palette[day["level"]]
        title = escape(f"{day['date']}: {count} GitHub contributions")
        if index == 0 or parsed.day == 1:
            months.append((x, f"{parsed:%b}"))
        if count == 0:
            buildings.append(f'<rect x="{x:.2f}" y="{baseline:.2f}" width="{bar_width:.2f}" height="1.5" fill="{palette[0]}" data-date="{day["date"]}" data-count="0"><title>{title}</title></rect>')
            continue
        top = baseline - bar_height
        buildings.append(
            f'<g><title>{title}</title>'
            f'<rect x="{x:.2f}" y="{top:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}" data-date="{day["date"]}" data-count="{count}"/>'
            f'<path d="M{x:.2f} {top:.2f}l{depth:.2f} {-depth:.2f}h{bar_width:.2f}l{-depth:.2f} {depth:.2f}Z" fill="{blend(color,.22)}"/>'
            f'<path d="M{x+bar_width:.2f} {top:.2f}l{depth:.2f} {-depth:.2f}v{bar_height:.2f}l{-depth:.2f} {depth:.2f}Z" fill="{color}" opacity=".55"/>'
            '</g>'
        )
    month_labels = "".join(
        f'<text x="{x:.2f}" y="{baseline+27}" fill="{muted}" font-family="Consolas,monospace" font-size="{16 if mobile else 14}">{label}</text>'
        for x, label in months
    )
    if mobile:
        labels = f'''
  <text x="28" y="41" fill="{ink}" font-family="Segoe UI,Arial,sans-serif" font-size="30" font-weight="600">Contribution skyline</text>
  <text x="26" y="108" fill="{ink}" font-family="Segoe UI,Arial,sans-serif" font-size="58" font-weight="700">{total:,}</text>
  <text x="155" y="89" fill="{muted}" font-family="Segoe UI,Arial,sans-serif" font-size="22">GitHub contributions</text>
  <text x="28" y="144" fill="{muted}" font-family="Segoe UI,Arial,sans-serif" font-size="20">{active} active days · {WEEKS} weeks · {short_date(first)} to {short_date(through)}</text>
  <text x="28" y="390" fill="{muted}" font-family="Consolas,monospace" font-size="16">PUBLIC CALENDAR / THROUGH {through.isoformat()} / UTC</text>'''
    else:
        labels = f'''
  <text x="32" y="44" fill="{gold if dark else '#002D62'}" font-family="Consolas,monospace" font-size="15" letter-spacing="1.3">GITHUB / CONTRIBUTION SKYLINE</text>
  <text x="29" y="139" fill="{ink}" font-family="Segoe UI,Arial,sans-serif" font-size="76" font-weight="700" letter-spacing="-2">{total:,}</text>
  <text x="33" y="174" fill="{muted}" font-family="Segoe UI,Arial,sans-serif" font-size="22">GitHub contributions</text>
  <text x="33" y="217" fill="{ink}" font-family="Segoe UI,Arial,sans-serif" font-size="20">{active} active days · {WEEKS} weeks</text>
  <text x="33" y="251" fill="{muted}" font-family="Segoe UI,Arial,sans-serif" font-size="18">{short_date(first)} to {short_date(through)}, {through.year}</text>
  <path d="M305 78V278" stroke="{rule}"/>
  <text x="33" y="317" fill="{muted}" font-family="Consolas,monospace" font-size="13">PUBLIC GITHUB CALENDAR · ONE BUILDING PER ACTIVE DAY · CALENDAR DATES ARE UTC · SNAPSHOT THROUGH {through.isoformat()}</text>'''
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc" data-total="{total}" data-active-days="{active}" data-days="{len(days)}">
  <title id="title">Contribution skyline</title>
  <desc id="desc">{total} GitHub contributions on {active} active days over {WEEKS} weeks, {first.isoformat()} to {through.isoformat()}. Each building represents an active day. Height is proportional to contribution count. Data is a dated snapshot of the publicly visible calendar.</desc>
  <rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="8" fill="{bg}" stroke="{rule}"/>
  <path d="M28 0H118" stroke="{gold}" stroke-width="3"/>
  <path d="M{chart_x} {baseline}H{chart_x+chart_width}" stroke="{rule}"/>
  {labels}
  {''.join(buildings)}
  {month_labels}
</svg>
'''
    return "\n".join(line.rstrip() for line in svg.splitlines()) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through", type=date.fromisoformat, required=True, help="Last GitHub calendar date (YYYY-MM-DD, UTC)")
    parser.add_argument("--html-file", type=Path, help="Use a saved anonymous public calendar response")
    parser.add_argument("--from-cache", action="store_true", help="Regenerate artwork from the saved JSON, without network requests")
    args = parser.parse_args()
    if args.from_cache and args.html_file:
        parser.error("--from-cache and --html-file cannot be combined")
    if args.from_cache:
        data = json.loads((OUTPUT / "calendar.json").read_text(encoding="utf-8"))
        if data["through"] != args.through.isoformat():
            parser.error("The requested date does not match the saved snapshot")
        first = date.fromisoformat(data["from"])
        days = data["days"]
    else:
        first, days, sources = collect_days(args.through, args.html_file)
        data = {
            "account": ACCOUNT, "from": first.isoformat(), "through": args.through.isoformat(),
            "weeks": WEEKS, "calendarTimezone": "UTC", "source": "Anonymous public GitHub contribution calendar",
            "sourceUrls": sources, "fetchedAtUtc": datetime.now(timezone.utc).isoformat(),
            "days": days,
        }
    if len(days) != WEEKS * 7 or len({day["date"] for day in days}) != len(days):
        raise ValueError("Expected exactly 168 distinct calendar days")
    if days[0]["date"] != first.isoformat() or days[-1]["date"] != args.through.isoformat():
        raise ValueError("Calendar range does not match the snapshot")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "calendar.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for suffix, dark, mobile in [("",True,False),("-light",False,False),("-mobile",True,True),("-mobile-light",False,True)]:
        (OUTPUT / f"skyline{suffix}.svg").write_text(render(days,first,args.through,dark,mobile),encoding="utf-8")
    readme = ROOT / "README.md"
    content = readme.read_text(encoding="utf-8")
    caption = f'A 24-week snapshot of my <a href="https://github.com/{ACCOUNT}?tab=overview">public GitHub calendar</a>, through {args.through:%B} {args.through.day}, {args.through.year}.'
    content, count = re.subn(r'A 24-week snapshot of my <a href="https://github.com/[^"]+">public GitHub calendar</a>, (?:refreshed|through) [^<]+',caption,content)
    if count != 1:
        raise ValueError("Could not update the README snapshot caption")
    readme.write_text(content,encoding="utf-8")
    print(json.dumps({"days":len(days),"contributions":sum(day["count"] for day in days),"activeDays":sum(day["count"]>0 for day in days),"from":first.isoformat(),"through":args.through.isoformat(),"svgVariants":4},indent=2))


if __name__ == "__main__":
    main()
