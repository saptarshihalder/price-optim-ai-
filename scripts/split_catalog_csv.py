#!/usr/bin/env python3
"""
Split the catalog file into multiple CSVs:

- product_data/catalog_categorized.csv: full table with slot + canonical term
- product_data/catalog_by_slot/<slot>.csv: one per slot/category
- product_data/catalog_by_term/<term>.csv: one per canonical search term

The input file is expected at repo root:
  Dzukou_Pricing_Overview_With_Names - Copy.csv

This script mirrors the backend's simple heuristics so it can be run
standalone without the web server.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List

ROOT = Path(__file__).resolve().parents[1]
INFILE = ROOT / "Dzukou_Pricing_Overview_With_Names - Copy.csv"
OUT_DIR = ROOT / "product_data"

SLOT_CATEGORIES: Dict[str, int] = {
    "Sunglasses": 15,
    "Bottles": 10,
    "Phone accessories": 10,
    "Notebook": 10,
    "Lunchbox": 10,
    "Premium shawls": 30,
    "Eri silk shawls": 20,
    "Cotton scarf": 15,
    "Other scarves and shawls": 15,
    "Cushion covers": 20,
    "Coasters & placements": 15,
    "Towels": 15,
}


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "items"


def strip_currency_to_float(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    try:
        m = re.findall(r"[\d\.,]+", s)
        if not m:
            return None
        return float(m[0].replace(",", "").strip())
    except Exception:
        return None


def canonical_term_for_item(name: str) -> str:
    n = (name or "").lower().strip()
    if any(k in n for k in ["phone stand", "mobile stand", "phone holder", "cell phone stand"]):
        return "phone stand"
    if any(k in n for k in ["sunglass", "sunglasses", "eyewear"]):
        if any(k in n for k in ["wood", "bamboo"]):
            return "wooden sunglasses"
        return "sunglasses"
    if any(k in n for k in ["bottle", "thermos", "flask"]):
        return "water bottle"
    if any(k in n for k in ["mug", "coffee mug", "tea mug", "cup"]):
        return "coffee mug"
    if any(k in n for k in ["notebook", "journal", "diary", "sketchbook"]):
        return "notebook"
    if any(k in n for k in ["lunch box", "lunchbox", "bento", "tiffin"]):
        return "lunch box"
    if "eri" in n and any(k in n for k in ["shawl", "stole"]):
        return "eri silk shawl"
    if any(k in n for k in ["pashmina", "cashmere", "merino", "yak"]) and any(k in n for k in ["shawl", "stole", "wrap"]):
        return "premium shawl"
    if "cotton" in n and any(k in n for k in ["scarf", "stole"]):
        return "cotton scarf"
    if any(k in n for k in ["scarf", "shawl", "stole", "wrap"]):
        return "shawl"
    if any(k in n for k in ["cushion cover", "pillow cover", "pillowcase", "cushion"]):
        return "cushion cover"
    if any(k in n for k in ["coaster", "placemat", "place mat", "table mat"]):
        return "coaster"
    if any(k in n for k in ["towel", "hand towel", "bath towel", "kitchen towel", "tea towel"]):
        return "towel"
    words = re.findall(r"[a-zA-Z]+", n)
    return (" ".join(words[:2]) if words else "product") or "product"


def slot_for_item(name: str) -> tuple[Optional[str], Optional[int]]:
    n = (name or "").lower()
    def slot(s: str) -> tuple[str, int]:
        return s, SLOT_CATEGORIES[s]
    if any(k in n for k in ["sunglass", "sunglasses", "eyewear"]):
        return slot("Sunglasses")
    if any(k in n for k in ["bottle", "thermos", "flask"]):
        return slot("Bottles")
    if ("phone" in n or "mobile" in n) and any(k in n for k in ["stand", "holder", "case", "accessory", "mount"]):
        return slot("Phone accessories")
    if any(k in n for k in ["notebook", "journal", "diary", "sketchbook"]):
        return slot("Notebook")
    if any(k in n for k in ["lunch box", "lunchbox", "bento", "tiffin"]):
        return slot("Lunchbox")
    if "eri" in n and any(k in n for k in ["shawl", "stole"]):
        return slot("Eri silk shawls")
    if any(k in n for k in ["pashmina", "cashmere", "merino", "yak"]) and any(k in n for k in ["shawl", "stole", "wrap"]):
        return slot("Premium shawls")
    if "cotton" in n and "scarf" in n:
        return slot("Cotton scarf")
    if any(k in n for k in ["scarf", "shawl", "stole", "wrap"]):
        return slot("Other scarves and shawls")
    if any(k in n for k in ["cushion", "pillow cover", "pillowcase"]):
        return slot("Cushion covers")
    if any(k in n for k in ["coaster", "placemat", "place mat", "table mat"]):
        return slot("Coasters & placements")
    if "towel" in n:
        return slot("Towels")
    return None, None


@dataclass
class CatalogItem:
    name: str
    code: Optional[str]
    price: Optional[float]
    cost: Optional[float]
    category: Optional[str]
    slot_percent: Optional[int]
    canonical_term: Optional[str]


def read_catalog() -> List[CatalogItem]:
    if not INFILE.exists():
        raise FileNotFoundError(f"Catalog not found: {INFILE}")
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    content: List[str] = []
    for enc in encodings:
        try:
            content = INFILE.read_text(encoding=enc).splitlines()
            break
        except Exception:
            continue
    reader = csv.reader(content)
    items: List[CatalogItem] = []
    for row in reader:
        if not row:
            continue
        name = (row[0] if len(row) > 0 else "").strip()
        if not name or name.lower().startswith("name"):
            continue
        code = (row[1] if len(row) > 1 else None)
        price = strip_currency_to_float(row[2] if len(row) > 2 else None)
        cost = strip_currency_to_float(row[3] if len(row) > 3 else None)
        term = canonical_term_for_item(name)
        cat, pct = slot_for_item(name)
        items.append(CatalogItem(name, code, price, cost, cat, pct, term))
    return items


def export_all(items: List[CatalogItem]) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Full categorized
    categorized = OUT_DIR / "catalog_categorized.csv"
    with categorized.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name","code","price","cost","category_slot","slot_percent","canonical_search_term"])
        for it in items:
            w.writerow([
                it.name,
                it.code or "",
                ("" if it.price is None else it.price),
                ("" if it.cost is None else it.cost),
                it.category or "Uncategorized",
                ("" if it.slot_percent is None else it.slot_percent),
                it.canonical_term or "",
            ])

    # Per slot
    by_slot_dir = OUT_DIR / "catalog_by_slot"
    by_slot_dir.mkdir(exist_ok=True)
    slots: Dict[str, List[CatalogItem]] = {}
    for it in items:
        slots.setdefault(it.category or "Uncategorized", []).append(it)
    by_slot_files: Dict[str, str] = {}
    for slot, rows in slots.items():
        p = by_slot_dir / f"{slugify(slot)}.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name","code","price","cost","canonical_search_term","slot_percent"])
            for it in rows:
                w.writerow([
                    it.name,
                    it.code or "",
                    ("" if it.price is None else it.price),
                    ("" if it.cost is None else it.cost),
                    it.canonical_term or "",
                    ("" if it.slot_percent is None else it.slot_percent),
                ])
        by_slot_files[slot] = str(p)

    # Per canonical term
    by_term_dir = OUT_DIR / "catalog_by_term"
    by_term_dir.mkdir(exist_ok=True)
    terms: Dict[str, List[CatalogItem]] = {}
    for it in items:
        terms.setdefault((it.canonical_term or "unknown").strip() or "unknown", []).append(it)
    by_term_files: Dict[str, str] = {}
    for term, rows in terms.items():
        p = by_term_dir / f"{slugify(term)}.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name","code","price","cost","category_slot","slot_percent"])
            for it in rows:
                w.writerow([
                    it.name,
                    it.code or "",
                    ("" if it.price is None else it.price),
                    ("" if it.cost is None else it.cost),
                    it.category or "Uncategorized",
                    ("" if it.slot_percent is None else it.slot_percent),
                ])
        by_term_files[term] = str(p)

    return {
        "categorized": str(categorized),
        "by_slot": by_slot_files,
        "by_term": by_term_files,
    }


def main():
    items = read_catalog()
    res = export_all(items)
    print("Wrote:")
    print("  ", res["categorized"])
    print("Per-slot:")
    for k, v in sorted(res["by_slot"].items()):
        print(f"  {k}: {v}")
    print("Per-term:")
    for k, v in sorted(res["by_term"].items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

