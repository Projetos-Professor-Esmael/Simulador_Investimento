"""Gera news.json a partir de feeds RSS oficiais/jornalísticos. Sem chave de API.
Cada item guarda título, link original, fonte e data. Itens parecidos de fontes
diferentes são agrupados e o campo "sources" indica quantas fontes cobriram o fato."""
import json, re, datetime as dt, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = {
    "Agência Brasil": "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",
    "g1 Economia": "https://g1.globo.com/rss/g1/economia/",
    "InfoMoney": "https://www.infomoney.com.br/feed/",
    "Banco Central": "https://www.bcb.gov.br/api/feed/sitebcb/sitefeeds/noticias",
}
STOP = set("de da do das dos a o e em para por com que um uma no na os as ao à se mais após diz vai".split())

def tokens(t): return {w for w in re.findall(r"\w+", t.lower()) if w not in STOP and len(w) > 2}

def parse_date(s):
    try: return parsedate_to_datetime(s).astimezone(dt.timezone.utc)
    except Exception:
        try: return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception: return None

def fetch(name, url):
    out = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-bot)"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=25).read())
        for it in root.iter("item"):
            t = (it.findtext("title") or "").strip(); l = (it.findtext("link") or "").strip()
            d = parse_date(it.findtext("pubDate") or "")
            if t and l.startswith("http") and d: out.append({"title": t, "link": l, "source": name, "published": d.isoformat()})
    except Exception as e:
        print("falha em", name, e)
    return out

items = [i for n, u in FEEDS.items() for i in fetch(n, u)]
cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)
items = [i for i in items if dt.datetime.fromisoformat(i["published"]) > cut]
items.sort(key=lambda i: i["published"], reverse=True)

groups = []
for i in items:
    tk = tokens(i["title"])
    for g in groups:
        if len(tk & g["tk"]) / max(1, len(tk | g["tk"])) > 0.45 and i["source"] not in g["srcs"]:
            g["srcs"].add(i["source"]); break
    else:
        groups.append({"item": i, "tk": tk, "srcs": {i["source"]}})
res = [{**g["item"], "sources": len(g["srcs"])} for g in groups]
res.sort(key=lambda i: (-(i["sources"] > 1), i["published"]), reverse=False)
res.sort(key=lambda i: (i["sources"] > 1, i["published"]), reverse=True)
json.dump({"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "items": res[:60]},
          open("news.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(res), "itens")
