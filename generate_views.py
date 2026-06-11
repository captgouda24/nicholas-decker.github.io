#!/usr/bin/env python3
"""
Generate the four reading-list HTML views from papers.json (the source of truth).

  reading-list.html              -> by tag   (primary; index.html links here)
  reading-list-by-author.html    -> by first-author surname
  reading-list-by-year.html      -> by year (newest first)
  reading-list-by-journal.html   -> by journal

Each paper appears under every one of its tags on the by-tag page. Links point
at the real on-disk PDF; genuinely-missing PDFs render as plain text (or a link
to the source URL if known) so there are no 404s. A build report verifies every
linked file exists.
"""
import os
import re
import json
import html

ROOT = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(ROOT, "pdfs")

NAV = [
    ("reading-list.html", "by tag"),
    ("reading-list-by-author.html", "by author"),
    ("reading-list-by-year.html", "by year"),
    ("reading-list-by-journal.html", "by journal"),
]


def esc(s):
    return html.escape(s or "", quote=False)


def page(title_words, current_file, sections_html):
    nav = []
    for fname, label in NAV:
        nav.append(label if fname == current_file
                   else f'<a href="{fname}">{label}</a>')
    nav_html = "\n    " + " | \n    ".join(["<a href=\"index.html\">back to main page</a>"] + nav)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="classic economics papers {esc(title_words)} - nicholas decker" />
  <title>reading list {esc(title_words)} - nicholas decker</title>
  <link rel="stylesheet" href="styles.css" />
</head>

<body>
  <div id="preamble">
   <a href="index.html"><h1 class="title">reading list {esc(title_words)}</h1></a>
   <h2 class="subtitle" style="margin-bottom: 35px;">{nav_html}
   </h2>
  </div>

  <div>
{sections_html}
  </div>
</body>
</html>
"""


def entry_li(p):
    """One <li> for a paper, matching the existing site format."""
    authors = esc(p["authors"])
    title = esc(p["title"])
    bits = [b for b in (p.get("year"), p.get("journal")) if b]
    tail = f" ({', '.join(esc(b) for b in bits)})" if bits else ""
    if not p["missing"] and p.get("pdf"):
        link = f'<a href="pdfs/{esc(p["pdf"])}">"{title}"</a>'
    elif p.get("url"):
        link = f'<a href="{esc(p["url"])}">"{title}"</a>'
    else:
        link = f'"{title}"'
    return f"  <li>{authors}: {link}{tail}</li>"


def section(heading, papers, sort_key):
    lis = "\n".join(entry_li(p) for p in sorted(papers, key=sort_key))
    return f"    <h2>{esc(heading)}</h2>\n<ul>\n{lis}\n</ul>\n"


def surname(p):
    return p["authors"].split(",")[0].strip()


def by_author_key(p):
    return (surname(p).lower(), p.get("year") or "9999")


def build(papers):
    # ---- by tag ----
    tags = sorted({t for p in papers for t in p["tags"]})
    secs = []
    for t in tags:
        members = [p for p in papers if t in p["tags"]]
        secs.append(section(t, members, by_author_key))
    untagged = [p for p in papers if not p["tags"]]
    if untagged:
        secs.append(section("Untagged", untagged, by_author_key))
    write("reading-list.html", page("by topic", "reading-list.html", "\n".join(secs)))

    # ---- by author ----
    surs = sorted({surname(p) for p in papers}, key=str.lower)
    secs = []
    for s in surs:
        members = [p for p in papers if surname(p) == s]
        secs.append(section(s, members, lambda p: p.get("year") or "9999"))
    write("reading-list-by-author.html",
          page("by author", "reading-list-by-author.html", "\n".join(secs)))

    # ---- by year (newest first; blanks last) ----
    years = sorted({p.get("year") or "" for p in papers},
                   key=lambda y: int(y) if y.isdigit() else -1, reverse=True)
    secs = []
    for y in years:
        members = [p for p in papers if (p.get("year") or "") == y]
        secs.append(section(y or "Undated / Working Papers", members,
                            lambda p: (surname(p).lower())))
    write("reading-list-by-year.html",
          page("by year", "reading-list-by-year.html", "\n".join(secs)))

    # ---- by journal ----
    journals = sorted({p.get("journal") or "" for p in papers},
                      key=lambda j: (j == "", j.lower()))
    secs = []
    for j in journals:
        members = [p for p in papers if (p.get("journal") or "") == j]
        secs.append(section(j or "Working Papers / Other", members, by_author_key))
    write("reading-list-by-journal.html",
          page("by journal", "reading-list-by-journal.html", "\n".join(secs)))


def write(fname, content):
    with open(os.path.join(ROOT, fname), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"wrote {fname}")


def main():
    with open(os.path.join(ROOT, "papers.json"), encoding="utf-8") as f:
        papers = json.load(f)
    build(papers)

    # ---- build report: verify every linked PDF exists ----
    on_disk = {f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")}
    linked = {p["pdf"] for p in papers if not p["missing"] and p.get("pdf")}
    broken = sorted(b for b in linked if b not in on_disk)
    missing = [p for p in papers if p["missing"]]
    print(f"\n{len(papers)} papers | {len(linked)} linked PDFs | "
          f"{len(broken)} broken links | {len(missing)} without a PDF")
    if broken:
        print("BROKEN (linked but not on disk):")
        for b in broken:
            print("  ", b)
    else:
        print("OK: every linked PDF exists on disk.")


if __name__ == "__main__":
    main()
