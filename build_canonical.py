#!/usr/bin/env python3
"""
Build the canonical papers dataset (papers.json) from the four existing
reading-list HTML views, deduplicating across views via signature clustering.

Output record per paper:
  authors, title, year, journal, url (source download, if known),
  pdf (canonical on-disk filename or null if missing), tags[], missing (bool)

Run:  python build_canonical.py
Then review papers.json + the printed report before generating HTML.
"""
import os
import re
import csv
import json
import html
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(ROOT, "pdfs")
# One-time migration: read the FROZEN original hand-maintained pages, never the
# generated output (which generate_views.py writes to ROOT). This decouples
# input from output so re-running can't feed the generator's pages back in.
SOURCE = os.path.join(ROOT, "legacy_source")

VIEWS = {
    "topic": "reading-list.html",
    "author": "reading-list-by-author.html",
    "year": "reading-list-by-year.html",
    "journal": "reading-list-by-journal.html",
}

# Compound topic category -> atomic tags (first pass; refine collaboratively).
TAG_MAP = {
    "Applied Empirical and General Data Wizardry": ["Applied Empirical"],
    "Behavioral Economics": ["Behavioral"],
    "Development": ["Development"],
    "Econometrics": ["Econometrics"],
    "Growth Macro": ["Growth", "Macro"],
    "Health and Insurance": ["Health", "Insurance"],
    "Industrial Organization, Estimation": ["Industrial Organization", "Estimation"],
    "Industrial Organization, Macro": ["Industrial Organization", "Macro"],
    "Industrial Organization, Media": ["Industrial Organization", "Media"],
    "Industrial Organization, Theory": ["Industrial Organization", "Theory"],
    "Innovation": ["Innovation"],
    "Labor Economics": ["Labor"],
    "Market Design": ["Market Design"],
    "Microeconomic Theory": ["Microeconomic Theory"],
    "Organizations and Mechanism Design": ["Organizations", "Mechanism Design"],
    "Political Economy": ["Political Economy"],
    "Price Indices": ["Price Indices"],
    "Spatial": ["Spatial"],
    "Taxation": ["Taxation", "Public"],
    "Trade": ["Trade"],
}

STOP = {"the", "a", "an", "of", "and", "in", "for", "to", "on", "with", "as",
        "is", "are", "from", "i", "ii", "iii", "same", "old", "or", "at", "by"}

# Hand-verified rescues: the link's intended filename -> the real on-disk file
# (case / typo / truncation drift that fuzzy matching can't safely resolve).
ALIAS = {
    "Ahlfeldt_2015_The_Economics_of_Density.pdf": "Ahlfeldt_The_Economics_Of.pdf",
    "Banerjee_The_Miracle_Of.pdf": "Banerjee_The_Miracle_of.pdf",
    "Chetty_Consumption_Commitments_And.pdf": "Chetty_Consumption_Committments_And.pdf",
    "Coase_1960_The_Problem_of_Social.pdf": "Coast_The_Problem_Of.pdf",
    "Milgrom_A_Theory_of.pdf": "Milgrom_A_Theory_Of.pdf",
    "Sanchez_de_la_Sierra_On_The_Origins.pdf": "Sanchez_De_La_Sierra_On_The_Origin.pdf",
}

LI_RE = re.compile(
    r'<li>\s*(?P<pre>.*?)<a href="(?P<href>pdfs/[^"]+)">\s*"?(?P<title>.*?)"?\s*</a>(?P<tail>.*?)</li>',
    re.DOTALL,
)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.DOTALL)


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s or "").strip())


def sig_words(text):
    toks = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return [t for t in toks if t not in STOP and not t.isdigit() and len(t) > 1]


def surname_key(authors):
    return authors.split(",")[0].strip().lower().replace(" ", "")[:5]


def parse_tail(tail):
    tail = clean(tail).strip("() ")
    m = re.search(r"\((.*?)\)", "(" + tail + ")")
    inside = clean(m.group(1)) if m else tail
    year, jparts = "", []
    for part in [p.strip() for p in inside.split(",") if p.strip()]:
        ym = re.search(r"\b(18|19|20)\d{2}\b", part)
        if ym and not year:
            year = ym.group(0)
            rest = (part[:ym.start()] + part[ym.end():]).strip(" ,")
            if rest:
                jparts.append(rest)
        else:
            jparts.append(part)
    return year, ", ".join(jparts)


def parse_view(path, is_topic):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    body = content.split("</head>", 1)[1] if "</head>" in content else content
    body = re.sub(r'<div id="preamble">.*?</div>', "", body, flags=re.DOTALL)
    headings = [(m.start(), clean(m.group(1))) for m in H2_RE.finditer(body)]

    def category_for(pos):
        cat = ""
        for start, txt in headings:
            if start < pos:
                cat = txt
            else:
                break
        return cat

    out = []
    for m in LI_RE.finditer(body):
        authors = clean(m.group("pre")).rstrip(":").strip()
        year, journal = parse_tail(m.group("tail"))
        out.append({
            "href": clean(m.group("href")),
            "authors": authors,
            "title": clean(m.group("title")),
            "year": year,
            "journal": journal,
            "category": category_for(m.start()) if is_topic else "",
            "words": set(sig_words(m.group("title"))),
            "skey": surname_key(authors),
        })
    return out


# ---- union-find ----
def make_uf(n):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    return find, union


def same_paper(a, b):
    if a["skey"] != b["skey"]:
        return False
    wa, wb = a["words"], b["words"]
    if not wa or not wb:
        return wa == wb
    # Subset handles subtitle variants ("...Mobility" vs "...Mobility: Childhood
    # Exposure..."). Otherwise require a strong overlap so two different papers
    # that merely share a couple of words (e.g. "common ownership") don't merge.
    if wa <= wb or wb <= wa:
        return True
    return len(wa & wb) >= 3


def load_source_urls():
    """Map signature -> source url from the (stale) classic_papers.csv."""
    urls = {}
    path = os.path.join(ROOT, "classic_papers.csv")
    if not os.path.exists(path):
        return urls
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("url"):
                continue
            key = (surname_key(row["authors"]), frozenset(sig_words(row["title"])))
            urls[key] = row["url"].strip()
    return urls


def main():
    entries = []
    for view, fname in VIEWS.items():
        es = parse_view(os.path.join(SOURCE, fname), is_topic=(view == "topic"))
        for e in es:
            e["view"] = view
        entries.extend(es)
        print(f"{fname:35s} -> {len(es)} entries")

    on_disk = {f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")} if os.path.isdir(PDF_DIR) else set()

    def file_sig(fname):
        parts = fname[:-4].split("_")
        surn = parts[0].strip().lower()[:5]
        words = {p.lower() for p in parts[1:]
                 if p and not p.isdigit() and p.lower() not in STOP and len(p) > 1}
        return surn, words

    disk_sigs = {f: file_sig(f) for f in on_disk}

    # Cluster entries that refer to the same paper.
    find, union = make_uf(len(entries))
    buckets = defaultdict(list)
    for i, e in enumerate(entries):
        buckets[e["skey"]].append(i)
    for idxs in buckets.values():
        for ii in range(len(idxs)):
            for jj in range(ii + 1, len(idxs)):
                if same_paper(entries[idxs[ii]], entries[idxs[jj]]):
                    union(idxs[ii], idxs[jj])

    clusters = defaultdict(list)
    for i in range(len(entries)):
        clusters[find(i)].append(entries[i])

    src_urls = load_source_urls()
    papers = []
    multi_title = []  # clusters with >1 distinct title -> eyeball for bad merges
    for members in clusters.values():
        # canonical pdf: an href whose file exists on disk, preferring the
        # non-"_YEAR_" scheme; else any existing; else mark missing.
        existing = [m["href"] for m in members
                    if os.path.basename(m["href"]) in on_disk]
        def score(h):
            base = os.path.basename(h)
            return (0 if re.search(r"_\d{4}_", base) else 1, len(base))
        pdf, missing, adopted = None, True, False
        if existing:
            pdf = os.path.basename(sorted(existing, key=score, reverse=True)[0])
            missing = False
        else:
            # No referenced file exists. Try to adopt an on-disk file (orphan)
            # that matches this paper's signature — catches case / underscore /
            # typo drift (real 404s on case-sensitive GitHub Pages).
            csurn = surname_key("".join(members[0]["authors"]))  # 5-char
            cwords = set()
            for m in members:
                cwords |= m["words"]
            best_f, best_n = None, 0
            for f, (fs, fw) in disk_sigs.items():
                if fs != csurn and not (fs.startswith(csurn[:4]) or csurn.startswith(fs[:4])):
                    continue
                n = len(cwords & fw)
                if n > best_n or (n == best_n and best_f and len(f) < len(best_f)):
                    best_f, best_n = f, n
            if best_f and (best_n >= 2 or (best_n >= 1 and len(cwords) <= 2)):
                pdf, missing, adopted = best_f, False, True
            else:
                # intended name = the most-plausible basename across views
                pdf = sorted((os.path.basename(m["href"]) for m in members),
                             key=lambda b: (0 if re.search(r"_\d{4}_", b) else 1, len(b)),
                             reverse=True)[0]

        def best(field):
            vals = [m[field] for m in members if m[field]]
            return max(vals, key=len) if vals else ""

        tags = set()
        for m in members:
            for t in TAG_MAP.get(m["category"], []):
                tags.add(t)

        title = best("title")
        authors = best("authors")
        key = (surname_key(authors), frozenset(sig_words(title)))
        url = src_urls.get(key, "")

        rec = {
            "authors": authors,
            "title": title,
            "year": best("year"),
            "journal": best("journal"),
            "url": url,
            "pdf": pdf,
            "tags": sorted(tags),
            "missing": missing,
            "adopted": adopted,
            "views": sorted({m["view"] for m in members}),
        }
        papers.append(rec)
        titles = {m["title"] for m in members if m["title"]}
        if len(titles) > 1:
            multi_title.append((rec, sorted(titles)))

    # Apply hand-verified filename rescues.
    for p in papers:
        if p["missing"] and p["pdf"] in ALIAS and ALIAS[p["pdf"]] in on_disk:
            p["pdf"], p["missing"], p["adopted"] = ALIAS[p["pdf"]], False, True

    papers.sort(key=lambda r: (r["authors"].lower(), r["year"]))

    missing = [p for p in papers if p["missing"]]
    adopted = [p for p in papers if p["adopted"]]
    untagged = [p for p in papers if not p["tags"]]
    all_tags = sorted({t for p in papers for t in p["tags"]})

    print(f"\n=== {len(papers)} canonical papers ===")
    print(f"  with PDF on disk : {len(papers) - len(missing)}")
    print(f"  of which re-linked to a drifted filename : {len(adopted)}")
    print(f"  MISSING pdf      : {len(missing)}")
    print(f"  untagged         : {len(untagged)}")

    print(f"\n=== RE-LINKED (link drift fixed by pointing at the real file) ({len(adopted)}) ===")
    for p in adopted:
        print(f"  {p['authors'].split(',')[0]} \"{p['title'][:45]}\" -> {p['pdf']}")
    print(f"\n=== {len(all_tags)} atomic tags ===")
    for t in all_tags:
        print(f"  {sum(1 for p in papers if t in p['tags']):3d}  {t}")

    print(f"\n=== MISSING PDFs ({len(missing)}) — the real download to-do ===")
    for p in missing:
        print(f"  {p['authors']}: \"{p['title']}\" ({p['year']}, {p['journal']}) [{p['pdf']}]")

    print(f"\n=== clusters with multiple distinct titles ({len(multi_title)}) — verify merges ===")
    for rec, titles in multi_title:
        print(f"  {rec['authors']}:")
        for t in titles:
            print(f"      - {t}")

    used = {p["pdf"] for p in papers if not p["missing"]}
    unused = sorted(f for f in on_disk if f not in used)
    print(f"\n=== UNUSED files still on disk ({len(unused)}) — possible matches for the missing ===")
    for f in unused:
        print(f"  {f}")

    # papers.json is the live source of truth once bootstrapped. Don't clobber
    # it on re-run (later additions live there) — write a comparison file instead.
    out = "papers.json"
    if os.path.exists(os.path.join(ROOT, "papers.json")):
        out = "papers.rebuilt.json"
        print("\nNOTE: papers.json exists; writing papers.rebuilt.json instead "
              "(this script is the one-time migration; edits go in papers.json).")
    with open(os.path.join(ROOT, out), "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out} ({len(papers)} papers).")


if __name__ == "__main__":
    main()
