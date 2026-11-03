"""Разовая отправка сводки новостей автобизнеса в Телеграм.
Запускается по расписанию в GitHub Actions (или вручную: python digest.py).

Переменные окружения:
  BOT_TOKEN  — токен бота от @BotFather
  CHAT_IDS   — chat ID получателей через запятую (свой ID узнать у @userinfobot)
"""
import html
import os
import sys
import time
import urllib.parse
import urllib.request

import feedparser

TOKEN = os.environ["BOT_TOKEN"]
CHAT_IDS = [c.strip() for c in os.environ["CHAT_IDS"].split(",") if c.strip()]
PER_SOURCE = 5  # заголовков с каждого источника

feedparser.USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AutoNewsBot/1.0"


def gnews(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=ru&gl=RU&ceid=RU:ru"
    )


FEEDS = {
    "Autonews": gnews("site:autonews.ru when:2d"),
    "Колёса": gnews("site:kolesa.ru when:2d"),
    "Motor": gnews("site:motor.ru when:2d"),
    "Drom": gnews("site:drom.ru when:2d"),
    "Autostat": gnews("site:autostat.ru when:7d"),
    "Автобизнес": gnews("автобизнес дилеры авторынок when:2d"),
}


def collect() -> dict[str, list[tuple[str, str]]]:
    result = {}
    for name, url in FEEDS.items():
        parsed = feedparser.parse(url)
        print(f"{name}: записей {len(parsed.entries)}", file=sys.stderr)
        items = [
            (e.get("title", "").strip(), e.get("link", ""))
            for e in parsed.entries[:PER_SOURCE]
            if e.get("title") and e.get("link")
        ]
        if items:
            result[name] = items
    return result


def build(data: dict) -> list[str]:
    blocks = []
    for name, items in data.items():
        lines = [f"<b>{html.escape(name)}</b>"]
        for title, link in items:
            lines.append(f'• <a href="{html.escape(link)}">{html.escape(title)}</a>')
        blocks.append("\n".join(lines))
    parts, current = [], "🚗 <b>Сводка новостей автобизнеса</b>"
    for b in blocks:
        if len(current) + len(b) + 2 > 3800:
            parts.append(current)
            current = ""
        current += ("\n\n" if current else "") + b
    parts.append(current)
    return parts


def send(chat_id: str, text: str) -> None:
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=body
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


if __name__ == "__main__":
    data = collect()
    if not data:
        sys.exit("Ни один источник не вернул новости")
    parts = build(data)
    for chat_id in CHAT_IDS:
        for p in parts:
            send(chat_id, p)
            time.sleep(0.2)
    print("Отправлено")
