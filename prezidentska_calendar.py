#!/usr/bin/env python3
"""
Prezidentská chata — ceny a dostupnost pokoje Vejminek pro 2 až 3
Použití: python3 prezidentska_calendar.py [počet_dní] [počet_dospělých]
Výchozí: 14 dní, 1 dospělý
Vždy generuje room.ics a index.html.
"""
import urllib.request
import json
import sys
from datetime import date, timedelta

ROOM_ID = 3101
API_BASE = "https://api.bookoloengine.com/desktop/v1/calendar/dynamic"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.prezidentska.cz/",
    "x-apikey": "n9s5xikttt",
    "x-currency": "CZK",
    "x-lang": "cs",
    "x-url": "https://www.prezidentska.cz/cs/rezervace",
    "x-account-token": "",
}
DAYS_CS = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]


def fetch_calendar(date_from: date, date_to: date, adults: int = 1) -> dict:
    params = (
        f"?dateFrom={date_from}"
        f"&dateTo={date_to}"
        f"&roomId={ROOM_ID}"
        f"&checkInDate={date_from}"
        f"&checkOutDate={date_to}"
        f"&adults={adults}"
        f"&promoCode=&voucherCode="
    )
    url = API_BASE + params
    print(f"GET {url}\n")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def format_price(price: float) -> str:
    if price == 0:
        return "    —    "
    return f"{price:>7,.0f} Kč".replace(",", " ")


def format_price_ics(price: float) -> str:
    return f"{price:.0f}"


def is_free(day: dict) -> bool:
    return not day["disabled"] and not day["occupied"] and day["closed"] is None


def status(day: dict) -> str:
    if day["disabled"]:
        return "⛔ Nedostupné"
    if is_free(day):
        return "✅ Volno"
    if day.get("closedToDeparture") and day["occupied"]:
        return "🔴 Obsazeno (odjezd)"
    if day.get("closedToArrival"):
        return "🔴 Obsazeno"
    return "🔴 Obsazeno"


def write_ics(values: dict, filename: str = "room.ics") -> None:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Prezidentska chata//Vejminek Availability//CS",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Vejminek – volné termíny",
    ]
    for day_str in sorted(values.keys()):
        day = values[day_str]
        if not is_free(day) or day["price"] == 0:
            continue
        d = date.fromisoformat(day_str)
        d_next = d + timedelta(days=1)
        lines += [
            "BEGIN:VEVENT",
            f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{d_next.strftime('%Y%m%d')}",
            f"SUMMARY:{format_price_ics(day['price'])}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")
    print(f"ICS uložen: {filename}")


def write_html(
    values: dict,
    date_from: date,
    date_to: date,
    days: int,
    adults: int,
    filename: str = "index.html",
) -> None:
    rows = []
    for day_str in sorted(values.keys()):
        day = values[day_str]
        d = date.fromisoformat(day_str)
        day_name = DAYS_CS[d.weekday()]
        price_str = format_price(day["price"]).strip()
        st = status(day)
        row_class = "free" if is_free(day) else "busy"
        rows.append(
            f'<tr class="{row_class}"><td>{d.strftime("%d. %m.")}</td>'
            f"<td>{day_name}</td><td>{price_str}</td><td>{st}</td></tr>"
        )
    rows_html = "\n".join(rows)
    updated = date.today().isoformat()
    html = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vejminek – dostupnost a ceny</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; margin-bottom: .4rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ padding: .4rem .8rem; text-align: left; border-bottom: 1px solid #e0e0e0; }}
  th {{ background: #f4f4f4; font-weight: 600; }}
  tr.free {{ background: #f0fff4; }}
  tr.busy td {{ color: #aaa; }}
  .meta {{ color: #555; font-size: .9rem; }}
  a {{ color: #2a7a4f; }}
</style>
</head>
<body>
<h1>Vejminek pro 2–3 osoby – dostupnost</h1>
<p class="meta">
  Termín: {date_from} – {date_to} ({days} nocí) · Dospělí: {adults}<br>
  Aktualizováno: {updated} ·
  <a href="room.ics">Přidat volné termíny do kalendáře (ICS)</a>
</p>
<table>
<thead><tr><th>Datum</th><th>Den</th><th>Cena/noc</th><th>Stav</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
</body>
</html>"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML uložen: {filename}")


def main() -> None:
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]

    days = int(positional[0]) if len(positional) > 0 else 14
    adults = int(positional[1]) if len(positional) > 1 else 1
    date_from = date.today()
    date_to = date_from + timedelta(days=days)

    data = fetch_calendar(date_from, date_to, adults)
    values = data.get("values", {})

    print(f"Pokoj:    Vejminek pro 2 až 3 (ID {ROOM_ID})")
    print(f"Termín:   {date_from} – {date_to}  ({days} nocí)")
    print(f"Dospělí: {adults}")
    print()
    print(f"{'Datum':<10} {'Den':<4} {'Cena/noc':>12}")
    print("-" * 30)
    for day_str in sorted(values.keys()):
        day = values[day_str]
        d = date.fromisoformat(day_str)
        day_name = DAYS_CS[d.weekday()]
        price_str = format_price(day["price"])
        print(f"{d.strftime('%d. %m.'):<10} {day_name:<4} {price_str}")
    print("-" * 30)

    write_ics(values)
    write_html(values, date_from, date_to, days, adults)


if __name__ == "__main__":
    main()
