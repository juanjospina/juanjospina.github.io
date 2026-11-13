#!/usr/bin/env python3
"""Sync the Publications section of index.html with Google Scholar.

    python3 scripts/update_publications.py            # fetch Scholar, update JSON + HTML
    python3 scripts/update_publications.py --offline  # re-render HTML from publications.json only

publications.json is the source of truth for everything you curate (title, authors,
venue, url, doi, cover, hide). Scholar only adds new entries and refreshes citation
counts / profile stats; it never overwrites fields you edited by hand.
New entries get their DOI from Crossref (exact title match) when possible.
Set "hide": true to drop an entry (slides, duplicates). Each entry is shown as a
navy tile: set "tile" (short venue name) and "type" (Journal, Conference, ...) to tune it.
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "publications.json"
INDEX = ROOT / "index.html"
SCHOLAR = "https://scholar.google.com"
PROFILE = f"{SCHOLAR}/citations?user=T39zSxsAAAAJ&hl=en"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
START, END = "<!-- PUBLICATIONS:START -->", "<!-- PUBLICATIONS:END -->"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def text(s):
    return html.unescape(re.sub(r"<.*?>", "", s)).strip()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def initials(authors):
    """Scholar's 'DM Fobes' -> 'D. M. Fobes', matching the hand-written entries."""
    return re.sub(r"\b([A-Z]+)(?= [A-Z][a-z])", lambda m: " ".join(c + "." for c in m.group(1)), authors)


def parse_scholar(page):
    """Return (stats, rows) from a Scholar profile page."""
    nums = [int(n) for n in re.findall(r'class="gsc_rsb_std">(\d+)', page)]
    stats = {"citations": nums[0], "h_index": nums[2], "i10_index": nums[4]} if len(nums) >= 6 else None
    rows = []
    for r in re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', page, re.S):
        link = re.search(r'href="([^"]*citation_for_view=[^"]*?:([\w-]+))"', r)
        title = re.search(r'class="gsc_a_at">(.*?)</a>', r, re.S)
        if not (link and title):
            continue
        gray = re.findall(r'<div class="gs_gray">(.*?)</div>', r, re.S) + ["", ""]
        cites = re.search(r'class="gsc_a_ac gs_ibl">(\d*)<', r)
        year = re.search(r'gsc_a_hc gs_ibl">(\d*)<', r)
        rows.append({
            "id": link.group(2),
            "scholar_url": SCHOLAR + html.unescape(link.group(1)),
            "title": text(title.group(1)),
            "authors": text(gray[0]),
            "venue": text(re.sub(r'<span class="gs_oph">.*?</span>', "", gray[1])),
            "year": int(year.group(1)) if year and year.group(1) else 0,
            "cites": int(cites.group(1)) if cites and cites.group(1) else 0,
        })
    return stats, rows


def fetch_scholar():
    stats, rows, start = None, [], 0
    while True:
        s, page = parse_scholar(get(f"{PROFILE}&cstart={start}&pagesize=100&sortby=pubdate"))
        stats = stats or s
        rows += page
        if len(page) < 100:
            break
        start += 100
    if not rows or not stats:
        sys.exit("Could not parse Google Scholar (blocked or captcha?). Nothing changed.")
    return stats, rows


def crossref(title):
    """Best-effort DOI lookup; only trusted on an exact (normalized) title match."""
    try:
        q = urllib.parse.quote(title)
        item = json.loads(get(f"https://api.crossref.org/works?rows=1&query.bibliographic={q}"))["message"]["items"][0]
    except Exception:
        return {}
    if norm(text((item.get("title") or [""])[0])) != norm(title):
        return {}
    authors = ", ".join(f"{a['given'][:1]}. {a['family']}" if a.get("given") else a.get("family", "")
                        for a in item.get("author", []))
    out = {"title": text(item["title"][0]), "doi": item["DOI"], "url": f"https://doi.org/{item['DOI']}"}
    if authors:
        out["authors"] = authors
    if item.get("container-title"):
        out["venue"] = text(item["container-title"][0])
    return out


def new_entry(row):
    e = {k: row[k] for k in ("title", "authors", "venue", "year")}
    e["authors"] = initials(e["authors"])
    e["url"] = row["scholar_url"]
    if not row["venue"] or "[slides]" in row["title"].lower():
        e["hide"] = True  # slides / placeholder entries Scholar picks up
    arxiv = re.search(r"arXiv:(\d{4}\.\d{4,5})", row["venue"])
    if arxiv:
        e["url"] = f"https://arxiv.org/abs/{arxiv.group(1)}"
    elif not e.get("hide"):
        e.update(crossref(row["title"]))
    return e


def merge(data, stats, rows):
    data["stats"] = {**stats, "updated": date.today().isoformat()}
    pubs = data.setdefault("publications", {})
    for row in rows:
        if row["id"] not in pubs:
            pubs[row["id"]] = new_entry(row)
            print("new:", row["title"])
            if any(norm(p["title"]) == norm(row["title"]) for k, p in pubs.items() if k != row["id"]):
                pubs[row["id"]]["hide"] = True  # already listed (e.g. added by hand before Scholar found it)
                print("  hidden: duplicate of an existing entry")
        pubs[row["id"]]["cites"] = row["cites"]
        pubs[row["id"]]["scholar_url"] = row["scholar_url"]


def esc(s):
    return html.escape(str(s), quote=True)


def safe_url(u):
    return esc(u) if str(u).startswith(("https://", "http://", "images/")) else "#"


def pub_type(venue):
    """Label for the top of the tile; override per entry with "type" in the JSON."""
    for word, label in (("arxiv", "Preprint"), ("patent", "Patent"), ("thesis", "Thesis"), ("workshop", "Workshop"),
                        ("conference|symposium|meeting|proceedings", "Conference")):
        if re.search(word, venue, re.I):
            return label
    return "Journal"


def render(data):
    st = data["stats"]
    updated = date.fromisoformat(st["updated"]).strftime("%B %Y")
    out = [
        '<div class="pub-stats">',
        f'  <div><span class="pub-stat">{st["citations"]:,}</span>Citations</div>',
        f'  <div><span class="pub-stat">{st["h_index"]}</span>h-index</div>',
        f'  <div><span class="pub-stat">{st["i10_index"]}</span>i10-index</div>',
        f'  <p class="pub-stats-note">From <a href="{esc(PROFILE)}">Google Scholar</a>, updated {updated}.</p>',
        "</div>",
    ]
    shown = [p for p in data["publications"].values() if not p.get("hide")]
    kind = lambda p: p.get("type") or pub_type(p.get("venue", ""))
    css = lambda t: "t-" + re.sub(r"[^a-z]", "", t.lower())  # colour per type lives in css/styles.css
    types = sorted({kind(p) for p in shown}, key=lambda t: [kind(p) for p in shown].count(t), reverse=True)
    count = lambda t: sum(kind(p) == t for p in shown)
    out.append('<div class="pub-legend" role="group" aria-label="Filter publications by type">'
               f'<button type="button" data-type="all" aria-pressed="true">All <span>{len(shown)}</span></button>'
               + "".join(f'<button type="button" class="{css(t)}" data-type="{css(t)}" aria-pressed="false">'
                         f'{esc(t)} <span>{count(t)}</span></button>' for t in types) + "</div>")
    out.append('<div class="pubs">')
    for p in sorted(shown, key=lambda p: -p.get("year", 0)):  # stable: keeps JSON order within a year
        url = safe_url(p.get("url") or p.get("scholar_url", ""))
        label = p.get("tile") or re.split(r",|\s\d|\spreprint", p.get("venue") or "")[0]
        tile = (f'<span class="pub-tile {css(kind(p))}"><small>{esc(kind(p))}</small>'
                f'{esc(label)}<b>{esc(p.get("year") or "")}</b></span>')
        authors = ", ".join(f"<strong>{esc(a)}</strong>" if "Ospina" in a else esc(a)
                            for a in p.get("authors", "").split(", "))
        authors = re.sub(r",\s*\.\.\.$", " et al.", authors)  # Scholar truncates long author lists
        venue = esc(p.get("venue", "")) + (f", {p['year']}" if p.get("year") and str(p["year"]) not in p.get("venue", "") else "")
        meta = []
        if p.get("cites"):
            meta.append(f'<a href="{safe_url(p.get("scholar_url", PROFILE))}">Cited by {p["cites"]}</a>')
        if p.get("doi"):
            meta.append(f'<span class="__dimensions_badge_embed__" data-doi="{esc(p["doi"])}" data-style="small_rectangle" data-hide-zero-citations="true"></span>')
        out += [
            f'  <article class="pub" data-type="{css(kind(p))}">',
            f'    <a class="pub-cover" href="{url}" tabindex="-1" aria-hidden="true">{tile}</a>',
            "    <div>",
            f'      <h3 class="pub-title"><a href="{url}">{esc(p["title"])}</a></h3>',
            f'      <p class="pub-authors">{authors}</p>',
            f'      <p class="pub-venue"><i>{venue}</i></p>',
            f'      <p class="pub-meta">{" ".join(meta)}</p>' if meta else "",
            "    </div>",
            "  </article>",
        ]
    out.append("</div>")
    return "\n".join(line for line in out if line)


def write_index(block):
    page = INDEX.read_text(encoding="utf-8")
    a, b = page.index(START) + len(START), page.index(END)
    indent = " " * 20
    INDEX.write_text(page[:a] + "\n" + "\n".join(indent + l for l in block.splitlines()) + "\n" + indent + page[b:],
                     encoding="utf-8")


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if "--offline" not in sys.argv:
        merge(data, *fetch_scholar())
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_index(render(data))
    print(f"{sum(not p.get('hide') for p in data['publications'].values())} publications rendered.")


if __name__ == "__main__":
    main()
