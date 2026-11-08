#!/usr/bin/env python3
"""Refresh the public directory of regional MCHS websites; do not parse alerts."""
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.request import Request, urlopen

SOURCE = "https://mchs.gov.ru/ministerstvo/glavnye-upravleniya-po-subektam-rossiyskoy-federacii"
OUT = "data/official-sources.json"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.text = []
        self.items = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []
    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            url = self.href.strip()
            name = " ".join(" ".join(self.text).split())
            if re.fullmatch(r"https://[a-z0-9.-]+\.mchs\.gov\.ru/?", url, re.I) and name:
                self.items.append({"name": name, "url": url.rstrip("/") + "/"})
            self.href = None
            self.text = []

req = Request(SOURCE, headers={"User-Agent": "RadarRU-public-source-directory/1.0"})
with urlopen(req, timeout=30) as response:
    page = response.read().decode("utf-8", "replace")
parser = Links()
parser.feed(page)
unique = {item["url"]: item for item in parser.items}
sources = sorted(unique.values(), key=lambda item: item["name"].casefold())
if not sources:
    raise SystemExit("No official regional MCHS links found; keeping previous data")
payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "directory_source": SOURCE,
    "sources": sources
}
with open(OUT, "w", encoding="utf-8") as file:
    json.dump(payload, file, ensure_ascii=False, indent=2)
    file.write("\n")
print(f"Updated {len(sources)} official regional source links")
