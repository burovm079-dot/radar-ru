#!/usr/bin/env python3
"""Refresh the public MCHS directory and check website reachability only; never parse alerts."""
import json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE="https://mchs.gov.ru/ministerstvo/glavnye-upravleniya-po-subektam-rossiyskoy-federacii"
OUT="data/official-sources.json"

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.href=None; self.text=[]; self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a": self.href=dict(attrs).get("href"); self.text=[]
    def handle_data(self,data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            url=self.href.strip(); name=" ".join(" ".join(self.text).split())
            if re.fullmatch(r"https://[a-z0-9.-]+\.mchs\.gov\.ru/?",url,re.I) and name:
                self.items.append({"name":name,"url":url.rstrip("/")+"/"})
            self.href=None; self.text=[]

def check_site(item):
    req=Request(item["url"],headers={"User-Agent":"RadarRU-source-availability-check/1.0","Range":"bytes=0-1023"})
    try:
        with urlopen(req,timeout=12) as response:
            response.read(1024)
            item["availability"]="available" if 200<=response.status<400 else "unavailable"
    except HTTPError as error:
        item["availability"]="available" if error.code in (401,403,405,429) else "unavailable"
    except (URLError,TimeoutError,OSError):
        item["availability"]="unavailable"
    item["checked_at"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
    return item

req=Request(SOURCE,headers={"User-Agent":"RadarRU-public-source-directory/1.0"})
with urlopen(req,timeout=30) as response: page=response.read().decode("utf-8","replace")
parser=Links(); parser.feed(page)
unique={item["url"]:item for item in parser.items}
sources=sorted(unique.values(),key=lambda item:item["name"].casefold())
if not sources: raise SystemExit("No official regional MCHS links found; keeping previous data")
with ThreadPoolExecutor(max_workers=12) as pool:
    futures=[pool.submit(check_site,item) for item in sources]
    checked=[future.result() for future in as_completed(futures)]
checked.sort(key=lambda item:item["name"].casefold())
payload={"updated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
 "directory_source":SOURCE,
 "status_meaning":"Website reachability only; not an emergency or alert status.",
 "sources":checked}
with open(OUT,"w",encoding="utf-8") as file:
    json.dump(payload,file,ensure_ascii=False,indent=2); file.write("\n")
available=sum(1 for item in checked if item["availability"]=="available")
print(f"Updated {len(checked)} source links; {available} websites responded")
