#!/usr/bin/env python3
"""
Add papers to papers.json (the source of truth), then run generate_views.py.

This batch folds in the 22 orphan PDFs that were already in pdfs/ but linked
from no view. Citations hand-entered; tags are a first pass (refine later).
De-dupes against existing entries by PDF filename and by author+title signature.
"""
import os
import re
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
STOP = {"the", "a", "an", "of", "and", "in", "for", "to", "on", "with", "as",
        "is", "are", "from", "i", "ii", "iii", "same", "old", "or", "at", "by"}


def sig(authors, title):
    surn = authors.split(",")[0].strip().lower().replace(" ", "")[:5]
    words = frozenset(t for t in re.sub(r"[^\w\s]", " ", title.lower()).split()
                      if t not in STOP and not t.isdigit() and len(t) > 1)
    return surn, words


def P(authors, title, year, journal, pdf, tags, url=""):
    return {"authors": authors, "title": title, "year": year, "journal": journal,
            "url": url, "pdf": pdf, "tags": sorted(tags), "missing": False,
            "adopted": False, "views": ["added"]}


NEW = [
    P("Bolotnyy, Valentin, Shoshana Vasserman",
      "Scaling Auctions as Insurance: A Case Study in Infrastructure Procurement",
      "2023", "ECTA", "Bolotnyy_Scaling_Auctions_As.pdf",
      ["Market Design", "Estimation", "Industrial Organization"]),
    P("Card, David, Alan Krueger",
      "Minimum Wages and Employment: A Case Study of the Fast-Food Industry in New Jersey and Pennsylvania",
      "1994", "AER", "Card_Minimum_Wages_And.pdf", ["Labor", "Applied Empirical"]),
    P("Duggan, Mark, Steven Levitt",
      "Winning Isn't Everything: Corruption in Sumo Wrestling",
      "2002", "AER", "Duggan_Winning_Isn't_Everything.pdf",
      ["Applied Empirical", "Behavioral"]),
    P("Hall, Robert, Charles Jones",
      "The Value of Life and the Rise in Health Spending",
      "2007", "QJE", "Hall_The_Value_Of.pdf", ["Health", "Macro"]),
    P("Jones, Charles, Pete Klenow",
      "Beyond GDP? Welfare across Countries and Time",
      "2016", "AER", "Jones_Beyond_GDP_Welfare.pdf",
      ["Growth", "Macro", "Applied Empirical"]),
    P("Jones, Charles",
      "Intermediate Goods and Weak Links in the Theory of Economic Development",
      "2011", "AEJ:Macro", "Jones_Intermediate_Goods_And.pdf",
      ["Growth", "Macro", "Development"]),
    P("Jones, Charles", "Life and Growth",
      "2016", "JPE", "Jones_Life_And_Growth.pdf", ["Growth", "Macro"]),
    P("Jones, Charles", "R&D-Based Models of Economic Growth",
      "1995", "JPE", "Jones_R&D_Based_Models.pdf", ["Growth", "Macro", "Innovation"]),
    P("Jones, Charles", "Time Series Tests of Endogenous Growth Models",
      "1995", "QJE", "Jones_Time_Series_Tests.pdf", ["Growth", "Macro", "Econometrics"]),
    P("Jones, Charles", "Why Have Health Expenditures as a Share of GDP Risen So Much?",
      "2002", "NBER", "Jones_Why_Have_Health.pdf", ["Health", "Macro"]),
    P("Bils, Mark, Pete Klenow", "Quantifying Quality Growth",
      "2001", "AER", "Klenow_Quantifying_Quality_Growth.pdf",
      ["Price Indices", "Innovation", "Macro"]),
    P("Kleven, Henrik", "Externalities and the Taxation of Top Earners",
      "2025", "NBER", "Kleven_Externalities_And_The.pdf", ["Taxation", "Public", "Macro"]),
    P("Larsen, Bradley, Carol Hengheng Lu, Anthony Lee Zhang",
      "Intermediaries in Bargaining: Evidence from Business-to-Business Used-Car Inventory Negotiations",
      "2021", "WP", "Larsen_Intermediaries_In_Bargaining.pdf",
      ["Market Design", "Estimation", "Industrial Organization"]),
    P("Larsen, Bradley",
      "The Efficiency of Real-World Bargaining: Evidence from Wholesale Used-Auto Auctions",
      "2021", "REStud", "Larsen_The_Efficiency_Of.pdf", ["Market Design", "Estimation"]),
    P("Lundborg, Petter, Erik Plug, Astrid Würtz Rasmussen",
      "Can Women Have Children and a Career? IV Evidence from IVF Treatments",
      "2017", "AER", "Lundborg_Can_Women_Have.pdf", ["Labor"]),
    P("Milgrom, Paul, John Roberts",
      "Price and Advertising Signals of Product Quality",
      "1986", "JPE", "Milgrom_Price_And_Advertising.pdf",
      ["Industrial Organization", "Theory"]),
    P("Mokyr, Joel",
      "The Lever of Riches: Technological Creativity and Economic Progress",
      "1990", "Oxford University Press", "Mokyr_The_Lever_Of.pdf",
      ["Growth", "Innovation"]),
    P("Mokyr, Joel",
      "Why Ireland Starved: A Quantitative and Analytical History of the Irish Economy, 1800-1850",
      "1983", "Routledge", "Mokyr_Why_Ireland_Starved.pdf",
      ["Development", "Applied Empirical"]),
    P("Myerson, Roger, Mark Satterthwaite",
      "Efficient Mechanisms for Bilateral Trading",
      "1983", "JET", "Myerson_Efficient_Mechanisms_For.pdf",
      ["Mechanism Design", "Microeconomic Theory"]),
    P("Sargent, Thomas, Neil Wallace",
      "'Rational' Expectations, the Optimal Monetary Instrument, and the Optimal Money Supply Rule",
      "1975", "JPE", "Sargent_Rational_Expectations_The.pdf", ["Macro"]),
    P("Sargent, Thomas, Neil Wallace", "Some Unpleasant Monetarist Arithmetic",
      "1981", "FRB Minneapolis", "Sargent_Some_Unpleasant_Monetarist.pdf", ["Macro"]),
    P("Temin, Peter", "Two Views of the British Industrial Revolution",
      "1997", "JEH", "Temin_Two_Views_Of.pdf", ["Growth", "Applied Empirical"]),
]


def main():
    path = os.path.join(ROOT, "papers.json")
    papers = json.load(open(path, encoding="utf-8"))
    have_pdf = {p.get("pdf") for p in papers}
    have_sig = {sig(p["authors"], p["title"]) for p in papers}

    added, skipped = 0, []
    for rec in NEW:
        if rec["pdf"] in have_pdf or sig(rec["authors"], rec["title"]) in have_sig:
            skipped.append(rec["pdf"])
            continue
        # verify the PDF really is on disk before linking
        if not os.path.exists(os.path.join(ROOT, "pdfs", rec["pdf"])):
            print(f"WARN: {rec['pdf']} not found on disk — skipping")
            skipped.append(rec["pdf"])
            continue
        papers.append(rec)
        have_pdf.add(rec["pdf"])
        have_sig.add(sig(rec["authors"], rec["title"]))
        added += 1

    papers.sort(key=lambda r: (r["authors"].split(",")[0].lower(), r.get("year") or ""))
    json.dump(papers, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"added {added}, skipped {len(skipped)} -> {len(papers)} total")
    if skipped:
        print("skipped:", ", ".join(skipped))


if __name__ == "__main__":
    main()
