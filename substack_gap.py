#!/usr/bin/env python3
"""
Cross-reference the Substack "100 Papers That Inspire Wonder" list against
papers.json, and report which are NOT yet on the site (the download to-do).
"""
import os
import re
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
STOP = {"the", "a", "an", "of", "and", "in", "for", "to", "on", "with", "as",
        "is", "are", "from", "i", "ii", "iii", "same", "old", "or", "at", "by",
        "how", "what", "who", "does", "do", "has", "it", "gone", "too", "far"}


def words(title):
    return {t for t in re.sub(r"[^\w\s]", " ", title.lower()).split()
            if t not in STOP and not t.isdigit() and len(t) > 1}


def skey(surname):
    return surname.strip().lower().replace(" ", "")[:5]


# (first-author surname, title) for the Substack 100.
SUBSTACK = [
    ("Chetty", "Moral Hazard vs Liquidity and Optimal Unemployment Insurance"),
    ("Klenow", "The Neoclassical Revival in Growth Economics"),
    ("Vatter", "Quality Disclosure and Regulation: Scoring Design in Medicare Advantage"),
    ("Chetty", "A New Method of Estimating Risk Aversion"),
    ("Backus", "Common Ownership and Competition in the Ready-To-Eat Cereal Industry"),
    ("Garg", "Can Industrial Policy Overcome Coordination Failures"),
    ("Olley", "The Dynamics of Productivity in the Telecommunications Equipment Industry"),
    ("Nevo", "Measuring Market Power in the Ready-To-Eat Cereal Industry"),
    ("Bresnahan", "Entry and Competition in Concentrated Markets"),
    ("Ludwig", "Machine Learning as a Tool for Hypothesis Generation"),
    ("Ahlfeldt", "The Economics of Density: Evidence from the Berlin Wall"),
    ("Donaldson", "Railroads of the Raj"),
    ("Kreindler", "Peak-Hour Road Congestion Pricing"),
    ("Currier", "Infrastructure Inequality: Who Bears the Cost of Road Roughness"),
    ("Melnikov", "Gangs, Labor Mobility, and Development"),
    ("Almagro", "Optimal Urban Transportation Policy: Evidence from Chicago"),
    ("Hill", "Race to the Bottom: Competition and Quality in Science"),
    ("Eliason", "How Acquisitions Affect Firm Behavior and Performance: Dialysis"),
    ("Asher", "The Long-Run Development Impacts of Agricultural Productivity Gains: Irrigation Canals in India"),
    ("Chetty", "The Impacts of Neighborhoods on Intergenerational Mobility I: Childhood Exposure Effects"),
    ("Gale", "College Admissions and the Stability of Marriage"),
    ("Vickrey", "Counterspeculation, Auctions, and Competitive Sealed Tenders"),
    ("Bulow", "Auction Versus Negotiations"),
    ("Jones", "The End of Economic Growth? Unintended Consequences of a Declining Population"),
    ("Kremer", "The O-Ring Theory of Economic Development"),
    ("Kremer", "Population Growth and Technological Change: One Million B.C. to 1990"),
    ("Banerjee", "A Simple Model of Herd Behavior"),
    ("Clark", "Why Isn't the Whole World Developed"),
    ("Anagol", "Continued Existence of Cows Disproves Central Tenets of Capitalism"),
    ("Bertrand", "How Much Should We Trust Differences-in-Differences Estimates"),
    ("Patel", "Floods"),
    ("Moscona", "Inappropriate Technology: Evidence from Global Agriculture"),
    ("Berry", "Foundations of Demand Estimation"),
    ("Myerson", "Incentive Compatibility and the Bargaining Problem"),
    ("Abadie", "The Economic Costs of Conflict: A Case Study of the Basque Country"),
    ("Bloom", "Are Ideas Getting Harder to Find"),
    ("Webb", "The Impact of Artificial Intelligence on the Labor Market"),
    ("Bloom", "Identifying Technology Spillovers and Product Market Rivalry"),
    ("Bloom", "Does Management Matter? Evidence from India"),
    ("Gentzkow", "What Drives Media Slant? Evidence from U.S. Daily Newspapers"),
    ("Akerlof", "The Market for Lemons: Quality Uncertainty and the Market Mechanism"),
    ("Kamenica", "Bayesian Persuasion"),
    ("Armona", "What is Newsworthy? Theory and Evidence"),
    ("Dellavigna", "Uniform Pricing in U.S. Retail Chains"),
    ("Martin", "Bias in Cable News: Persuasion and Polarization"),
    ("Acemoglu", "The Colonial Origins of Comparative Development"),
    ("Levitt", "How Dangerous Are Drinking Drivers"),
    ("Kremer", "Worms: Identifying Impacts on Education and Health"),
    ("Walker", "Slack and Economic Development"),
    ("Nordhaus", "Do Real-Output and Real-Wage Measures Capture Reality? The History of Lighting"),
    ("Einav", "Estimating Welfare in Insurance Markets Using Variation in Prices"),
    ("Acemoglu", "Market Size in Innovation: Pharmaceutical Industry"),
    ("Atkin", "The Returns to Face-to-Face Interactions: Knowledge Spillovers in Silicon Valley"),
    ("Kalyani", "The Creativity Decline and the US Productivity Slowdown"),
    ("Kremer", "Patent Buyouts: A Mechanism for Encouraging Innovation"),
    ("Lundborg", "Can Women Have Children and a Career? IV Evidence from IVF Treatments"),
    ("Bolotnyy", "Why Do Women Earn Less than Men? Evidence from Bus and Train Operators"),
    ("Sanchez de la Sierra", "On the Origins of the State: Stationary Bandits and Taxation in Eastern Congo"),
    ("Dubois", "Bargaining and International Reference Pricing in the Pharmaceutical Industry"),
    ("Lucking-Reiley", "Field Experiments on the Effects of Reserve Prices in Auctions"),
    ("Larsen", "Intermediaries in Bargaining: Business-to-Business Used-Car Inventory Negotiations"),
    ("Jaravel", "The Unequal Gains From Product Innovations: U.S. Retail Sector"),
    ("Hamilton", "Using Engel's Law to Estimate CPI Bias"),
    ("Williams", "Intellectual Property Rights and Innovation: Evidence from the Human Genome"),
    ("Diamond", "A Model of Price Adjustment"),
    ("Diamond", "Aggregate Demand Management in Search Equilibrium"),
    ("Read", "Diversification Bias: Variety Seeking Between Combined and Separated Choices"),
    ("Atkin", "Organization Barriers to Technology Adoption: Soccer-Ball Producers in Pakistan"),
    ("Alesina", "On the Origins of Gender Roles: Women and the Plough"),
    ("Alesina", "A Positive Theory of Fiscal Deficits and Government Debt"),
    ("Coase", "Durability and Monopoly"),
    ("Bilbiie", "HANKSSON"),
    ("Ganong", "Earnings Instability"),
    ("Miller", "Understanding the Price Effects of the MillerCoors Joint Venture"),
    ("Alesina", "Persistence Through Revolutions"),
    ("Nakamura", "The Elusive Costs of Inflation: Price Dispersion During the US Great Inflation"),
    ("Hsieh", "The Life Cycle of Plants in India and Mexico"),
    ("Bils", "Quantifying Quality Growth"),
    ("Bulow", "The Simple Economics of Optimal Auctions"),
    ("Igami", "Measuring the Incentive to Collude: The Vitamin Cartels"),
    ("Eaton", "Putting Ricardo to Work"),
    ("Glosten", "Bid, Ask, and Transaction Prices in a Specialist Market"),
    ("Milgrom", "Information, Trade and Common Knowledge"),
    ("Schmitz", "What Determines Productivity? Iron Ore Industries"),
    ("Temin", "Two Views of the British Industrial Revolution"),
    ("Oberfield", "Inequality and Measured Growth"),
    ("Castillo", "Who Benefits from Surge Pricing"),
    ("Musolff", "Algorithmic Pricing, Price Wars and Tacit Collusion: E-Commerce"),
    ("Byrne", "Asymmetric Information Sharing in Oligopoly: Retail Gasoline"),
    ("Fisman", "Corruption, Norms, and Legal Enforcement: Diplomatic Parking Tickets"),
    ("Hastings", "How Are SNAP Benefits Spent? Evidence from a Retail Panel"),
    ("Shapiro", "Is There a Daily Discount Rate? Food Stamp Nutrition Cycle"),
    ("Kydland", "Rules Rather Than Discretion: The Inconsistency of Optimal Plans"),
    ("Eden", "The Cross-Sectional Implications of the Social Discount Rate"),
    ("Rollet", "Zoning and the Dynamics of Urban Redevelopment"),
    ("Noy", "The Business of the Culture War"),
    ("Holmstrom", "Understanding the Role of Debt in the Financial System"),
    ("Lucas", "On the Mechanics of Economic Development"),
    ("Radford", "The Economic Organization of a P.O.W Camp"),
    ("Akerman", "Public R&D Meets Economic Development: Embrapa and Brazil"),
]


def main():
    papers = json.load(open(os.path.join(ROOT, "papers.json"), encoding="utf-8"))
    idx = []
    for p in papers:
        idx.append((skey(p["authors"].split(",")[0]), words(p["title"]),
                    p["authors"], p["title"], p.get("missing")))

    present, missing_pdf, absent = [], [], []
    for surn, title in SUBSTACK:
        sw, sk = words(title), skey(surn)
        hit = None
        for k, pw, au, ti, miss in idx:
            if k != sk and not (k.startswith(sk[:4]) or sk.startswith(k[:4])):
                continue
            if sw <= pw or pw <= sw or len(sw & pw) >= 2:
                hit = (au, ti, miss)
                break
        if hit is None:
            absent.append((surn, title))
        elif hit[2]:
            missing_pdf.append((surn, title))
        else:
            present.append((surn, title))

    print(f"Substack 100 — cross-referenced against {len(papers)} site papers\n")
    print(f"  on site, PDF hosted : {len(present)}")
    print(f"  on site, PDF MISSING: {len(missing_pdf)}")
    print(f"  NOT on site yet     : {len(absent)}")

    print(f"\n=== NOT ON SITE YET ({len(absent)}) — download these ===")
    for s, t in absent:
        print(f"  {s}: {t}")
    print(f"\n=== ON SITE BUT PDF MISSING ({len(missing_pdf)}) ===")
    for s, t in missing_pdf:
        print(f"  {s}: {t}")


if __name__ == "__main__":
    main()
