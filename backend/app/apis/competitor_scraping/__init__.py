



from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
import traceback
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set
import asyncio
import aiohttp
import time
import random
from dataclasses import dataclass
from enum import Enum
import json
import re
from urllib.parse import urljoin, urlparse
from pathlib import Path
import csv
from datetime import datetime, timedelta
from collections import deque
try:
    import httpx
except Exception:  # Defer hard import errors to runtime usage paths
    httpx = None  # type: ignore
from bs4 import BeautifulSoup
from app.libs.product_matcher import create_product_matcher, ProductMatch
from app.libs.database import (
    save_scraped_products,
    save_scraped_products_for_run,
    create_scraping_run,
    update_scraping_run,
    finalize_scraping_run,
)

router = APIRouter()

class ScrapingStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class StoreInfo(BaseModel):
    name: str
    base_url: str
    search_path: str = "/search"
    is_shopify: Optional[bool] = None
    rate_limit: float = 1.0  # requests per second

class ScrapedProduct(BaseModel):
    store_name: str
    product_id: Optional[str] = None
    title: str
    price: Optional[float] = None
    currency: str = "USD"
    brand: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    product_url: str
    in_stock: bool = True
    scraped_at: datetime
    search_term: Optional[str] = None
    match_score: Optional[float] = None
    match_confidence: Optional[str] = None
    match_reasoning: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class ScrapingProgress(BaseModel):
    status: ScrapingStatus
    current_store: Optional[str] = None
    completed_stores: int = 0
    total_stores: int = 0
    products_found: int = 0
    errors: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ScrapingRequest(BaseModel):
    target_products: List[str]  # Product names to search for
    # Interpret this as the desired minimum products with price per store per search term
    max_products_per_store: int = 17

class ScrapingResponse(BaseModel):
    task_id: str
    status: ScrapingStatus
    message: str

class CatalogItem(BaseModel):
    name: str
    code: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    category: Optional[str] = None
    slot_percent: Optional[int] = None
    canonical_term: Optional[str] = None

# Target competitor stores
TARGET_STORES = [
    StoreInfo(name="Made Trade", base_url="https://www.madetrade.com", search_path="/search"),
    StoreInfo(name="EarthHero", base_url="https://earthhero.com", search_path="/search"),
    StoreInfo(name="GOODEE", base_url="https://www.goodeeworld.com", search_path="/search"),
    StoreInfo(name="Package Free Shop", base_url="https://packagefreeshop.com", search_path="/search"),
    StoreInfo(name="The Citizenry", base_url="https://www.thecitizenry.com", search_path="/search"),
    StoreInfo(name="Ten Thousand Villages", base_url="https://www.tenthousandvillages.com", search_path="/search"),
    StoreInfo(name="NOVICA", base_url="https://www.novica.com", search_path="/search"),
    StoreInfo(name="The Little Market", base_url="https://thelittlemarket.com", search_path="/search"),
    StoreInfo(name="DoneGood", base_url="https://donegood.co", search_path="/search"),
    StoreInfo(name="Folksy", base_url="https://folksy.com", search_path="/search"),
    StoreInfo(name="IndieCart", base_url="https://indiecart.com", search_path="/search"),
    StoreInfo(name="Zero Waste Store", base_url="https://zerowaste.store", search_path="/search"),
    StoreInfo(name="EcoRoots", base_url="https://ecoroots.us", search_path="/search"),
    StoreInfo(name="Wild Minimalist", base_url="https://wildminimalist.com", search_path="/search"),
    StoreInfo(name="Green Eco Dream", base_url="https://greenecodream.com", search_path="/search")
]

# Global storage for scraping tasks
scraping_tasks: Dict[str, ScrapingProgress] = {}
scraping_results: Dict[str, List[ScrapedProduct]] = {}

# Map store names to base URLs for CSV export convenience
STORE_URL_BY_NAME: Dict[str, str] = {s.name: s.base_url for s in TARGET_STORES}

# Slot categories with preferred margin percentages (provided by user)
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


def _slugify(term: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (term or "").strip().lower()).strip("_")
    return s or "products"


def _pluralize_label(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    # Naive pluralization for display (Coffee Mug -> Coffee Mugs)
    if s.endswith("s"):
        return s
    return s + "s"


def _pluralize_slug(slug: str) -> str:
    if not slug:
        return slug
    if slug.endswith("s"):
        return slug
    return slug + "s"


def _export_products_csv(products: List[ScrapedProduct], search_term: str) -> Path:
    """Write a single CSV file with scraped data only.

    Columns: category, store, product_name, price, search_term, store_url
    Output path: repo_root/product_data/<slug>.csv (e.g., product_data/coffee_mugs.csv)
    """
    # Resolve repo root from this file location: backend/app/apis/competitor_scraping/__init__.py
    repo_root = Path(__file__).resolve().parents[4]
    out_dir = repo_root / "product_data"
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = _pluralize_slug(_slugify(search_term))
    out_path = out_dir / f"{slug}.csv"

    # Derive a category from the search term for display purposes
    category = _pluralize_label(search_term.strip().title())

    # Filter rows to only those for this term when available
    filtered = [p for p in products if (p.search_term or "").strip().lower() == search_term.strip().lower()]
    rows = filtered if filtered else products

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "store", "product_name", "price", "search_term", "store_url"])
        for p in rows:
            store = p.store_name
            store_url = STORE_URL_BY_NAME.get(store)
            if not store_url:
                try:
                    store_url = f"{urlparse(p.product_url).scheme}://{urlparse(p.product_url).netloc}"
                except Exception:
                    store_url = ""
            writer.writerow([
                category,
                store or "",
                p.title or "",
                ("" if p.price is None else p.price),
                search_term,
                store_url or "",
            ])
    return out_path

def _strip_currency_to_float(s: str | None) -> Optional[float]:
    if not s:
        return None
    try:
        # Remove everything except digits, comma and dot
        m = re.findall(r"[\d\.,]+", s)
        if not m:
            return None
        t = m[0].replace(",", "").strip()
        return float(t) if t else None
    except Exception:
        return None

def _canonical_term_for_item(name: str) -> str:
    """Map a product name to a generic search term used across competitors.

    This intentionally prefers broad terms; our scraper later expands to synonyms.
    """
    n = (name or "").lower().strip()
    # Specific common items first
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
    # Fallback to a cleaned term
    # keep 2 important words
    words = re.findall(r"[a-zA-Z]+", n)
    base = " ".join(words[:2]) if words else "product"
    return base or "product"

def _slot_for_item(name: str) -> tuple[Optional[str], Optional[int]]:
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

def _read_catalog_csv() -> list[CatalogItem]:
    """Load catalog CSV from repo root and return parsed items with inferred fields."""
    # Resolve repo root as in _export_products_csv
    repo_root = Path(__file__).resolve().parents[4]
    csv_path = repo_root / "Dzukou_Pricing_Overview_With_Names - Copy.csv"
    items: list[CatalogItem] = []
    if not csv_path.exists():
        return items
    # Try utf-8-sig, fallback to latin-1
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    content: list[str] = []
    for enc in encodings:
        try:
            content = csv_path.read_text(encoding=enc).splitlines()
            break
        except Exception:
            continue
    reader = csv.reader(content)
    for row in reader:
        if not row:
            continue
        # Expect: name, code, price, cost (best effort)
        name = (row[0] if len(row) > 0 else "").strip()
        if not name or name.lower().startswith("name"):
            continue
        code = (row[1] if len(row) > 1 else None)
        price = _strip_currency_to_float(row[2] if len(row) > 2 else None)
        cost = _strip_currency_to_float(row[3] if len(row) > 3 else None)
        term = _canonical_term_for_item(name)
        cat, pct = _slot_for_item(name)
        items.append(CatalogItem(name=name, code=code, price=price, cost=cost, category=cat, slot_percent=pct, canonical_term=term))
    return items

def _export_catalog_assignment(items: list[CatalogItem]) -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    out_dir = repo_root / "product_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "catalog_categorized.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "code", "price", "cost", "category_slot", "slot_percent", "canonical_search_term"])
        for it in items:
            writer.writerow([
                it.name,
                it.code or "",
                ("" if it.price is None else it.price),
                ("" if it.cost is None else it.cost),
                it.category or "Uncategorized",
                ("" if it.slot_percent is None else it.slot_percent),
                it.canonical_term or "",
            ])
    return out_path

def _export_catalog_per_slot(items: list[CatalogItem]) -> Dict[str, Path]:
    """Create a separate CSV for each slot/category with the catalog rows belonging to it."""
    repo_root = Path(__file__).resolve().parents[4]
    out_dir = repo_root / "product_data" / "catalog_by_slot"
    out_dir.mkdir(parents=True, exist_ok=True)
    grouped: Dict[str, list[CatalogItem]] = {}
    for it in items:
        key = it.category or "Uncategorized"
        grouped.setdefault(key, []).append(it)
    paths: Dict[str, Path] = {}
    for slot, rows in grouped.items():
        slug = _slugify(slot)
        p = out_dir / f"{slug}.csv"
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
        paths[slot] = p
    return paths

def _export_catalog_per_term(items: list[CatalogItem]) -> Dict[str, Path]:
    """Create a separate CSV for each canonical search term with the catalog rows mapped to it."""
    repo_root = Path(__file__).resolve().parents[4]
    out_dir = repo_root / "product_data" / "catalog_by_term"
    out_dir.mkdir(parents=True, exist_ok=True)
    grouped: Dict[str, list[CatalogItem]] = {}
    for it in items:
        key = (it.canonical_term or "").strip() or "unknown"
        grouped.setdefault(key, []).append(it)
    paths: Dict[str, Path] = {}
    for term, rows in grouped.items():
        slug = _slugify(term)
        p = out_dir / f"{slug}.csv"
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
        paths[term] = p
    return paths

class TokenBucket:
    """Rate limiting using token bucket algorithm"""
    def __init__(self, rate: float, capacity: float = None):
        self.rate = rate  # tokens per second
        self.capacity = capacity or rate * 2
        self.tokens = self.capacity
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + (now - self.last_update) * self.rate)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                # Wait time to get next token
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
                return True

class CompetitorScraper:
    def __init__(self):
        self.rate_limiters = {store.name: TokenBucket(store.rate_limit) for store in TARGET_STORES}
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def detect_shopify(self, url: str) -> bool:
        """Detect if a site is using Shopify"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    # Common Shopify indicators
                    shopify_indicators = [
                        'Shopify.theme',
                        'shopify.com',
                        'cdn.shopify.com',
                        'window.Shopify',
                        'shopify-section'
                    ]
                    return any(indicator in text for indicator in shopify_indicators)
        except Exception as e:
            print(f"Error detecting Shopify for {url}: {e}")
        return False
    
    async def extract_json_ld(self, html: str) -> List[Dict]:
        """Extract JSON-LD structured data"""
        json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>'
        matches = re.findall(json_ld_pattern, html, re.IGNORECASE)
        
        json_ld_data = []
        for match in matches:
            try:
                data = json.loads(match.strip())
                json_ld_data.append(data)
            except json.JSONDecodeError:
                continue
        
        return json_ld_data
    
    async def extract_microdata(self, html: str) -> Dict[str, Any]:
        """Extract microdata structured information"""
        # Simple microdata extraction for products
        product_data = {}
        
        # Extract price
        price_patterns = [
            r'itemprop=["\']price["\'][^>]*content=["\']([^"\']*)["\']',
            r'<span[^>]*itemprop=["\']price["\'][^>]*>([^<]*)</span>',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                try:
                    price_text = match.group(1).strip()
                    # Extract numeric price
                    price_num = re.search(r'[\d,]+\.?\d*', price_text)
                    if price_num:
                        product_data['price'] = float(price_num.group().replace(',', ''))
                        break
                except (ValueError, AttributeError):
                    continue
        
        return product_data
    
    async def scrape_product_page(self, url: str, store_name: str, search_term: Optional[str] = None) -> Optional[ScrapedProduct]:
        """Scrape individual product page"""
        try:
            # Skip obvious non-product URLs
            if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif', '.svg', '.ico', '.css', '.js']):
                return None
                
            await self.rate_limiters[store_name].acquire()
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type and 'application' not in content_type:
                    return None
                
                html = await response.text()
                
                # Extract structured data
                json_ld_data = await self.extract_json_ld(html)
                microdata = await self.extract_microdata(html)
                
                # Initialize product data
                product = ScrapedProduct(
                    store_name=store_name,
                    product_url=url,
                    title="",
                    scraped_at=datetime.now(),
                    raw_data={'html_length': len(html)}
                )
                product.search_term = (search_term or "").strip() or None
                
                # Extract from JSON-LD first (most reliable)
                for data in json_ld_data:
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        product.title = data.get('name', '')
                        product.description = data.get('description', '')
                        product.brand = data.get('brand', {}).get('name') if isinstance(data.get('brand'), dict) else data.get('brand')
                        product.image_url = data.get('image', [None])[0] if isinstance(data.get('image'), list) else data.get('image')
                        
                        # Extract price from offers
                        offers = data.get('offers', {})
                        if isinstance(offers, dict):
                            price_text = offers.get('price') or offers.get('lowPrice')
                            if price_text:
                                try:
                                    product.price = float(str(price_text).replace(',', ''))
                                    product.currency = offers.get('priceCurrency', 'USD')
                                except ValueError:
                                    pass
                            
                            # Check availability
                            availability = offers.get('availability', '')
                            product.in_stock = 'instock' in availability.lower() if availability else True
                        break
                
                # Fallback to microdata if JSON-LD didn't work
                if not product.price and microdata.get('price'):
                    product.price = microdata['price']
                
                # Fallback to HTML parsing if structured data failed
                if not product.title:
                    title_patterns = [
                        r'<title[^>]*>([^<]*)</title>',
                        r'<h1[^>]*>([^<]*)</h1>',
                        r'property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']',
                    ]
                    for pattern in title_patterns:
                        match = re.search(pattern, html, re.IGNORECASE)
                        if match:
                            product.title = match.group(1).strip()
                            break
                
                # Enhanced price extraction if still missing
                if not product.price:
                    price_patterns = [
                        r'["\']price["\']\s*:\s*["\']?([\d,]+\.?\d*)["\']?',
                        r'\$([\d,]+\.?\d*)',
                        r'€([\d,]+\.?\d*)',
                        r'£([\d,]+\.?\d*)',
                        r'class=["\'][^"\']*(price|cost)[^"\']*(["\']).+?([\d,]+\.?\d*)',
                    ]
                    for pattern in price_patterns:
                        try:
                            matches = re.findall(pattern, html, re.IGNORECASE)
                            if matches:
                                price_match = matches[0]
                                if isinstance(price_match, tuple):
                                    # Find the numeric part in the tuple
                                    for part in price_match:
                                        if re.match(r'^[\d,]+\.?\d*$', str(part)):
                                            product.price = float(str(part).replace(',', ''))
                                            break
                                else:
                                    product.price = float(str(price_match).replace(',', ''))
                                break
                        except (ValueError, IndexError, re.error):
                            continue
                # One more pass for common international currency symbols
                if not product.price:
                    extra_price_patterns = [
                        r'€\s*([\d\.,]+)',
                        r'£\s*([\d\.,]+)',
                        r'₹\s*([\d\.,]+)',
                        r'INR\s*([\d\.,]+)',
                        r'Rs\.?\s*([\d\.,]+)'
                    ]
                    for pattern in extra_price_patterns:
                        try:
                            m = re.search(pattern, html, re.IGNORECASE)
                            if m:
                                product.price = float(m.group(1).replace(',', '').strip())
                                break
                        except Exception:
                            continue
                
                # Extract brand if missing
                if not product.brand:
                    match = re.search(r'"brand"\s*:\s*"([^\"]+)"', html, re.IGNORECASE)
                    if match:
                        product.brand = match.group(1).strip()
                
                # Basic authenticity filter: skip obvious test/demo/sample products
                def is_authentic(title: str, page_url: str) -> bool:
                    t = (title or "").lower()
                    u = (page_url or "").lower()
                    banned = [
                        "test ", " sample", "demo", "lorem", "ipsum", "dummy", "placeholder",
                        "template", "mock ", "coming soon", "pre-order sample", "qa ",
                    ]
                    if any(b in t for b in banned):
                        return False
                    if any(b in u for b in ["/test", "/sample", "/demo", "/placeholder"]):
                        return False
                    return True

                valid = bool(product.title) and (product.price is not None)
                if not valid:
                    return None
                if not is_authentic(product.title or "", url):
                    return None
                return product
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    async def search_store(self, store: StoreInfo, query: str, min_products: int, target_product: str) -> List[ScrapedProduct]:
        """Search for products in a specific store with enhanced methods and pagination.

        Ensures at least ``min_products`` items with price are returned when possible.
        """
        products: List[ScrapedProduct] = []
        matcher = create_product_matcher()

        desired = max(17, min_products)

        try:
            # Detect if Shopify (enables extra endpoints)
            is_shopify = await self.detect_shopify(store.base_url)

            def generate_search_terms(term: str) -> List[str]:
                t = term.lower()
                terms = {t}
                # Simple synonym expansion to improve recall
                if "wooden" in t:
                    terms.update({t.replace("wooden", "wood"), t.replace("wooden", "bamboo")})
                if "sunglass" in t:
                    terms.update({t.replace("sunglasses", "shades"), t.replace("sunglass", "glasses")})
                if "thermos" in t or "bottle" in t:
                    terms.update({t.replace("thermos", "insulated"), t + " flask"})
                if "mug" in t:
                    terms.add("coffee mug")
                if "phone stand" in t:
                    terms.update({t.replace("phone stand", "phone holder"), "mobile stand"})
                if "lunchbox" in t:
                    terms.update({"lunch box", "bento box"})
                if "silk" in t and "stole" in t:
                    terms.update({t.replace("stole", "scarf"), t.replace("stole", "shawl")})
                return list(terms)

            async def collect_urls_for_term(term: str, page: int = 1) -> List[str]:
                q = re.sub(r"\s+", "+", term.strip())
                endpoints = [
                    f"{store.base_url}{store.search_path}?q={q}",
                    f"{store.base_url}/search?q={q}",
                    f"{store.base_url}/search?query={q}",
                    f"{store.base_url}/search?s={q}",
                    f"{store.base_url}/catalogsearch/result/?q={q}",
                ]
                if page > 1:
                    endpoints.extend([
                        f"{store.base_url}{store.search_path}?q={q}&page={page}",
                        f"{store.base_url}/search?q={q}&page={page}",
                        f"{store.base_url}/search?query={q}&page={page}",
                        f"{store.base_url}/collections/all?q={q}&page={page}",
                        f"{store.base_url}/collections/all?sort_by=best-selling&q={q}&page={page}",
                    ])
                if is_shopify:
                    endpoints.extend([
                        f"{store.base_url}/collections/all?q={q}",
                        f"{store.base_url}/search/suggest.json?q={q}&resources[type]=product&resources[limit]=20",
                    ])

                product_urls: set[str] = set()
                for url in endpoints:
                    try:
                        await self.rate_limiters[store.name].acquire()
                        async with self.session.get(url) as resp:
                            if resp.status != 200:
                                continue
                            # JSON suggest endpoint
                            ct = resp.headers.get("Content-Type", "")
                            if url.endswith("suggest.json") or "json" in ct:
                                try:
                                    data = await resp.json()
                                    # Common Shopify suggest shapes
                                    candidates = []
                                    if isinstance(data, dict):
                                        # Newer format
                                        resources = data.get("resources") or {}
                                        results = resources.get("results") or {}
                                        candidates.extend(results.get("products", []))
                                        # Older format
                                        if not candidates and "products" in data:
                                            candidates = data["products"]
                                    for p in candidates:
                                        href = p.get("url") or p.get("url_with_domain")
                                        if href:
                                            product_urls.add(urljoin(store.base_url, href))
                                except Exception:
                                    pass
                                continue

                            html = await resp.text()
                            # Harvest from JSON-LD ItemList if present
                            try:
                                for m in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html, re.IGNORECASE):
                                    try:
                                        data = json.loads(m.strip())
                                        items = []
                                        if isinstance(data, dict) and data.get("@type") == "ItemList":
                                            items = data.get("itemListElement", [])
                                        if isinstance(items, list):
                                            for it in items:
                                                if isinstance(it, dict):
                                                    url_field = it.get("url") or (it.get("item") or {}).get("url")
                                                    if url_field:
                                                        product_urls.add(urljoin(store.base_url, url_field))
                                    except Exception:
                                        continue
                            except Exception:
                                pass

                            # Regex-based URL harvesting
                            url_patterns = [
                                r'href=["\']([^"\']*/products?/[^"\']*)["\']',
                                r'href=["\']([^"\']*/collections/[^"\']*/products/[^"\']*)["\']',
                                r'href=["\']([^"\']*/items?/[^"\']*)["\']',
                                r'href=["\']([^"\']*/product/[^"\']*)["\']',
                                r'href=["\']([^"\']*/shop/[^"\']*)["\']',
                                r'<a[^>]*href=["\']([^"\']*/[^"\']*(product|item)[^"\']*)["\']',
                            ]
                            for pattern in url_patterns:
                                matches = re.findall(pattern, html, re.IGNORECASE)
                                for match in matches:
                                    u = match if isinstance(match, str) else match[0]
                                    if u.startswith('/'):
                                        full = urljoin(store.base_url, u)
                                    elif u.startswith('http'):
                                        full = u
                                    else:
                                        continue
                                    low = full.lower()
                                    if any(skip in low for skip in ['cart', 'account', 'login', 'contact', 'about', 'blog', 'news', 'policy', 'terms', 'faq', 'support', 'help']):
                                        continue
                                    if any(ext in low for ext in ['.jpg', '.png', '.gif', '.svg', '.ico', '.css', '.js', '.pdf', '.zip']):
                                        continue
                                    product_urls.add(full)
                    except Exception:
                        continue
                return list(product_urls)

            # Multi-strategy harvesting until we meet desired minimum per term
            scraped_count = 0
            seen_urls: set[str] = set()
            for term in generate_search_terms(query):
                page = 1
                # Try up to 12 pages or until we hit desired
                while scraped_count < desired and page <= 12:
                    urls = await collect_urls_for_term(term, page)
                    new_urls = [u for u in urls if u not in seen_urls]
                    if not new_urls:
                        page += 1
                        continue
                    seen_urls.update(new_urls)
                    for url in new_urls:
                        if scraped_count >= desired:
                            break
                        product = await self.scrape_product_page(url, store.name, target_product)
                        if product and product.price is not None:
                            # Apply product matching
                            match_result = matcher.match_product(target_product, {
                                'title': product.title,
                                'brand': product.brand,
                                'description': product.description
                            })
                            # Lower threshold slightly to meet minimum while keeping relevance
                            if match_result.similarity_score >= 0.05:
                                product.match_score = match_result.similarity_score
                                product.match_confidence = match_result.confidence
                                product.match_reasoning = match_result.reasoning
                                products.append(product)
                                scraped_count += 1
                                # small pacing
                                await asyncio.sleep(0.25)
                    page += 1
                if scraped_count < desired:
                    # As a last resort for this term, relax matching threshold slightly and retry
                    for url in list(seen_urls):
                        if scraped_count >= desired:
                            break
                        product = await self.scrape_product_page(url, store.name, target_product)
                        if product and product.price is not None and (product.match_score or 0) < 0.05:
                            products.append(product)
                            scraped_count += 1
                            await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error searching {store.name}: {e}")

        # Sort by match score and trim (ensure at least desired items if available)
        products.sort(key=lambda p: p.match_score or 0, reverse=True)
        return products[: max(desired, len(products))]

async def scrape_competitors_background(task_id: str, request: ScrapingRequest):
    """Background task for scraping competitors"""
    progress = scraping_tasks[task_id]
    progress.status = ScrapingStatus.RUNNING
    progress.started_at = datetime.now()
    progress.total_stores = len(TARGET_STORES)
    # Persist run start
    try:
        await create_scraping_run(task_id, request.target_products, progress.total_stores)
    except Exception as e:
        print(f"Failed to persist scraping run start: {e}")
    
    all_products = []
    
    try:
        async with CompetitorScraper() as scraper:
            # Process stores concurrently with controlled concurrency
            semaphore = asyncio.Semaphore(3)  # Limit concurrent stores
            
            async def scrape_store_with_progress(store: StoreInfo):
                async with semaphore:
                    progress.current_store = store.name
                    print(f"Starting scraping for {store.name}")
                    
                    store_products = []
                    for product_name in request.target_products:
                        print(f"Searching for '{product_name}' in {store.name}")
                        products = await scraper.search_store(store, product_name, request.max_products_per_store, product_name)
                        store_products.extend(products)
                        
                        # Add delay between product searches
                        await asyncio.sleep(1.0)
                    
                    # Persist incrementally to storage (best-effort) for this run and latest snapshot
                    if store_products:
                        try:
                            await save_scraped_products_for_run(store_products, task_id)
                        except Exception as e:
                            print(f"Store-level save failed for {store.name}: {e}")

                    progress.completed_stores += 1
                    progress.products_found += len(store_products)
                    print(f"Completed {store.name}: found {len(store_products)} products")
                    try:
                        await update_scraping_run(task_id, progress.completed_stores, progress.products_found)
                    except Exception as e:
                        print(f"Failed to update run progress: {e}")
                    
                    return store_products
            
            # Execute all store scraping tasks
            tasks = [scrape_store_with_progress(store) for store in TARGET_STORES]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    progress.errors.append(f"Error scraping {TARGET_STORES[i].name}: {str(result)}")
                else:
                    all_products.extend(result)

        # Mark task as completed before any optional persistence work
        # Also normalize counters and clear transient state so the UI reflects completion immediately
        progress.status = ScrapingStatus.COMPLETED
        progress.completed_at = datetime.now()
        try:
            progress.completed_stores = progress.total_stores or progress.completed_stores
        except Exception:
            pass
        # Ensure we don't keep showing a stale "currently scraping" store in the UI
        progress.current_store = None

        # Store results in memory
        scraping_results[task_id] = all_products

        # Persist final snapshot (best-effort) also update run status
        try:
            if all_products:
                await save_scraped_products_for_run(all_products, task_id)
        except Exception as e:
            print(f"Skipping final DB persistence: {e}")
        try:
            await finalize_scraping_run(task_id, 'completed')
        except Exception as e:
            print(f"Failed to finalize run: {e}")
        
        # Export one CSV per search term, filtered to that term's rows
        try:
            for term in request.target_products or []:
                path = _export_products_csv(all_products, term)
                print(f"CSV exported to {path}")
        except Exception as e:
            print(f"CSV export failed: {e}")
        
    except Exception as e:
        # Treat missing Databutton project id as non-fatal in local/dev
        msg = str(e)
        if "DATABUTTON_PROJECT_ID" in msg or "databutton project id" in msg.lower():
            # Ensure results are accessible even if persistence failed
            scraping_results[task_id] = all_products
            progress.status = ScrapingStatus.COMPLETED
            progress.errors.append(
                "Skipped persistence: missing Databutton config. Scrape completed successfully."
            )
        else:
            progress.status = ScrapingStatus.FAILED
            tb = traceback.format_exc()
            progress.errors.append(f"Fatal error: {msg}\n{tb}")
        progress.completed_at = datetime.now()
        # Clear transient state on terminal states (completed/failed)
        progress.current_store = None
        try:
            await finalize_scraping_run(task_id, progress.status.value if isinstance(progress.status, ScrapingStatus) else str(progress.status))
        except Exception as e2:
            print(f"Failed to finalize run on error: {e2}")

# -------------------------
# Resilient round-robin scraper
# -------------------------

@dataclass
class StoreStatus:
    name: str
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    is_blocked: bool = False
    retry_after: Optional[datetime] = None
    rate_limit_delay: float = 1.0


class ResilientScraper:
    def __init__(self):
        # Round-robin queue of stores to scrape
        self.store_queue = deque(TARGET_STORES)
        self.store_status: Dict[str, StoreStatus] = {
            store.name: StoreStatus(store.name) for store in TARGET_STORES
        }

        # Failed stores that need retry later
        self.retry_queue: List[StoreInfo] = []

        # Current session
        self.client: Optional["httpx.AsyncClient"] = None

        # Delays and limits
        self.base_delay = (2, 8)  # Random delay between requests (min, max seconds)
        self.store_switch_delay = (5, 15)  # Delay when switching stores
        self.max_consecutive_failures = 3
        self.retry_cooldown = timedelta(minutes=30)  # Wait 30min before retrying blocked store

    def get_random_headers(self) -> Dict[str, str]:
        """Generate realistic, randomized browser headers"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

        accept_languages = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.8,es;q=0.7',
            'en-CA,en;q=0.9',
        ]

        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(accept_languages),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }

    async def __aenter__(self):
        if httpx is None:
            raise RuntimeError("httpx is required for ResilientScraper. Please install 'httpx'.")
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
            # Don't reuse connections too aggressively
            transport=httpx.AsyncHTTPTransport(retries=1)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def get_next_store(self) -> Optional[StoreInfo]:
        """Get next available store from round-robin queue"""
        now = datetime.now()

        # Check retry queue first for stores that might be ready
        ready_retries = []
        for store in self.retry_queue[:]:
            status = self.store_status[store.name]
            if status.retry_after and now >= status.retry_after:
                ready_retries.append(store)
                self.retry_queue.remove(store)
                self.store_queue.append(store)
                status.is_blocked = False
                status.consecutive_failures = 0

        if ready_retries:
            print(f"Re-enabled {len(ready_retries)} stores from retry queue")

        # Try to find an available store
        attempts = 0
        while attempts < len(self.store_queue) * 2:  # Prevent infinite loop
            if not self.store_queue:
                break

            store = self.store_queue.popleft()
            status = self.store_status[store.name]

            if not status.is_blocked:
                # Put it back at end of queue for next round
                self.store_queue.append(store)
                return store

            # Store is blocked, keep it out of main queue
            attempts += 1

        return None

    def mark_store_success(self, store_name: str):
        """Mark a store as successfully scraped"""
        status = self.store_status[store_name]
        status.last_success = datetime.now()
        status.consecutive_failures = 0
        status.is_blocked = False
        print(f"✅ {store_name}: Success")

    def mark_store_failure(self, store_name: str, error: str):
        """Mark a store as failed and potentially block it"""
        status = self.store_status[store_name]
        status.last_failure = datetime.now()
        status.consecutive_failures += 1

        print(f"❌ {store_name}: Failure #{status.consecutive_failures} - {error}")

        # Block store if too many consecutive failures
        if status.consecutive_failures >= self.max_consecutive_failures:
            status.is_blocked = True
            status.retry_after = datetime.now() + self.retry_cooldown

            # Move store to retry queue
            store = next((s for s in self.store_queue if s.name == store_name), None)
            if store:
                self.store_queue.remove(store)
                self.retry_queue.append(store)

            print(f"🚫 {store_name}: Blocked until {status.retry_after}")

    async def random_delay(self, delay_range: tuple = None):
        """Add random delay to avoid detection"""
        if delay_range is None:
            delay_range = self.base_delay

        delay = random.uniform(delay_range[0], delay_range[1])
        print(f"⏳ Waiting {delay:.1f}s...")
        await asyncio.sleep(delay)

    async def scrape_with_bs4(self, url: str, store_name: str) -> Optional[ScrapedProduct]:
        """Scrape a single product page with BeautifulSoup"""
        try:
            assert self.client is not None
            # Random headers per request
            headers = self.get_random_headers()

            response = await self.client.get(url, headers=headers)

            # Handle different HTTP errors
            if response.status_code == 429:
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            elif response.status_code == 403:
                raise httpx.HTTPStatusError("Forbidden/Blocked", request=response.request, response=response)
            elif response.status_code >= 400:
                raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)

            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract product data (simplified for example)
            title = self.extract_title(soup)
            price = self.extract_price(soup, response.text)

            if not title or price is None:
                return None

            return ScrapedProduct(
                store_name=store_name,
                product_url=url,
                title=title,
                price=price,
                scraped_at=datetime.now()
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception("Rate limited")
            elif e.response.status_code == 403:
                raise Exception("IP blocked")
            else:
                raise Exception(f"HTTP error {e.response.status_code}")
        except httpx.TimeoutException:
            raise Exception("Request timeout")
        except Exception as e:
            raise Exception(f"Scraping error: {str(e)}")

    def extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title with fallbacks"""
        selectors = [
            'h1.product-title',
            'h1[data-testid="product-title"]',
            '.product-name h1',
            'h1[itemprop="name"]',
            'h1',
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)[:200]  # Limit length
        return None

    def extract_price(self, soup: BeautifulSoup, html_text: str) -> Optional[float]:
        """Extract price with multiple fallbacks"""

        # Try CSS selectors first
        price_selectors = [
            '[data-testid="price"]',
            '.price-current',
            '.product-price',
            '.price',
            '[itemprop="price"]',
        ]

        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get_text(strip=True)
                price = self.parse_price_text(price_text)
                if price:
                    return price

        # Fallback to regex
        price_patterns = [
            r'\$([0-9,]+\.?[0-9]*)',
            r'€([0-9,]+\.?[0-9]*)',
            r'£([0-9,]+\.?[0-9]*)',
        ]

        for pattern in price_patterns:
            matches = re.findall(pattern, html_text)
            if matches:
                try:
                    return float(matches[0].replace(',', ''))
                except ValueError:
                    continue

        return None

    def parse_price_text(self, text: str) -> Optional[float]:
        """Parse price from text string"""
        if not text:
            return None

        price_match = re.search(r'([0-9,]+\.?[0-9]*)', text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group(1))
            except ValueError:
                pass
        return None

    async def scrape_stores_round_robin(self, search_terms: List[str], max_products: int = 50) -> List[ScrapedProduct]:
        """Main scraping method with round-robin and failure handling"""
        all_products: List[ScrapedProduct] = []
        total_scraped = 0

        print(f"🚀 Starting round-robin scraping for {len(search_terms)} terms")
        print(f"📊 Available stores: {len(self.store_queue)}")

        while total_scraped < max_products and (self.store_queue or self.retry_queue):
            store = self.get_next_store()

            if not store:
                print("⚠️  No available stores, waiting for retry cooldowns...")
                await asyncio.sleep(60)  # Wait 1 minute before checking retry queue
                continue

            print(f"\n🎯 Switching to {store.name}")
            await self.random_delay(self.store_switch_delay)

            # Try to scrape this store
            try:
                store_products = await self.scrape_store(store, search_terms)

                if store_products:
                    all_products.extend(store_products)
                    total_scraped += len(store_products)
                    self.mark_store_success(store.name)
                    print(f"✅ Got {len(store_products)} products from {store.name}")
                else:
                    print(f"📭 No products found at {store.name}")
                    # Don't mark as failure if no products, just no results

                # Always delay between stores
                await self.random_delay()

            except Exception as e:
                error_msg = str(e)
                self.mark_store_failure(store.name, error_msg)

                # Longer delay after failures
                await self.random_delay((10, 20))

        print(f"\n🏁 Scraping complete: {total_scraped} total products from {len(set(p.store_name for p in all_products))} stores")
        return all_products

    async def scrape_store(self, store: StoreInfo, search_terms: List[str]) -> List[ScrapedProduct]:
        """Scrape a single store for all search terms"""
        products: List[ScrapedProduct] = []
        assert self.client is not None

        for term in search_terms:
            try:
                # Find product URLs for this term
                search_url = f"{store.base_url}/search?q={term.replace(' ', '+')}"

                # Get search results page
                headers = self.get_random_headers()
                response = await self.client.get(search_url, headers=headers)

                if response.status_code != 200:
                    continue

                # Extract product URLs (simplified)
                soup = BeautifulSoup(response.text, 'html.parser')
                product_links = soup.find_all('a', href=True)

                product_urls: List[str] = []
                for link in product_links:
                    href = link['href']
                    if '/product' in href.lower():
                        if href.startswith('/'):
                            href = store.base_url + href
                        product_urls.append(href)

                # Limit products per search term
                product_urls = product_urls[:5]

                # Scrape each product
                for url in product_urls:
                    try:
                        product = await self.scrape_with_bs4(url, store.name)
                        if product:
                            product.search_term = term
                            products.append(product)

                        # Small delay between products
                        await self.random_delay((1, 3))

                    except Exception as e:
                        print(f"⚠️  Failed to scrape {url}: {e}")
                        continue

                # Delay between search terms
                await self.random_delay((2, 5))

            except Exception as e:
                print(f"⚠️  Failed search for '{term}' on {store.name}: {e}")
                continue

        return products


async def scrape_competitors_resilient(task_id: str, request: ScrapingRequest):
    """Updated background task using resilient round-robin scraper"""
    progress = scraping_tasks[task_id]
    progress.status = ScrapingStatus.RUNNING
    progress.started_at = datetime.now()

    try:
        async with ResilientScraper() as scraper:
            products = await scraper.scrape_stores_round_robin(
                request.target_products,
                request.max_products_per_store * len(TARGET_STORES)
            )

            # Store results
            scraping_results[task_id] = products
            progress.products_found = len(products)
            progress.status = ScrapingStatus.COMPLETED
            progress.completed_at = datetime.now()

    except Exception as e:
        progress.status = ScrapingStatus.FAILED
        progress.errors.append(str(e))
        progress.completed_at = datetime.now()

@router.post("/start-scraping")
async def start_scraping(req: Request, background_tasks: BackgroundTasks) -> ScrapingResponse:
    """Start competitor price scraping (accepts flexible body and safe defaults).

    This handler is resilient to missing/invalid JSON bodies and will fall back to
    a sensible default target list so that the UI never errors out on 4xx.
    """
    try:
        body = await req.json()
    except Exception:
        body = {}

    try:
        targets = body.get("target_products") or ["Coffee Mug"]
        if not isinstance(targets, list):
            targets = [str(targets)]
        targets = [str(t) for t in targets if str(t).strip()]
        if not targets:
            targets = ["Coffee Mug"]
        max_per_store = body.get("max_products_per_store") or 17
        try:
            max_per_store = int(max_per_store)
        except Exception:
            max_per_store = 17
        sr = ScrapingRequest(target_products=targets, max_products_per_store=max_per_store)
    except Exception:
        sr = ScrapingRequest(target_products=["Coffee Mug"], max_products_per_store=17)

    task_id = f"scrape_{int(time.time())}"

    # Initialize progress tracking and mark as running immediately so UI reflects start
    scraping_tasks[task_id] = ScrapingProgress(
        status=ScrapingStatus.RUNNING,
        total_stores=len(TARGET_STORES),
        started_at=datetime.now(),
        completed_stores=0,
        products_found=0,
        errors=[],
    )

    # Start background task
    background_tasks.add_task(scrape_competitors_background, task_id, sr)

    return ScrapingResponse(
        task_id=task_id,
        status=ScrapingStatus.RUNNING,
        message="Scraping task started successfully"
    )

@router.options("/start-scraping")
async def start_scraping_options() -> dict:
    # Useful if a browser sends a preflight; being explicit avoids surprises
    return {"ok": True}

@router.get("/start-scraping")
async def start_scraping_get(background_tasks: BackgroundTasks) -> ScrapingResponse:
    """Convenience GET variant to start a scrape with default targets.

    This covers clients that accidentally call GET instead of POST or cannot send a body.
    """
    sr = ScrapingRequest(target_products=["Coffee Mug"], max_products_per_store=17)
    task_id = f"scrape_{int(time.time())}"
    scraping_tasks[task_id] = ScrapingProgress(
        status=ScrapingStatus.RUNNING,
        total_stores=len(TARGET_STORES),
        started_at=datetime.now(),
    )
    background_tasks.add_task(scrape_competitors_background, task_id, sr)
    return ScrapingResponse(task_id=task_id, status=ScrapingStatus.RUNNING, message="Scraping task started successfully")

# Compatibility routes for builds that call /api/routes/*
@router.post("/api/routes/start-scraping")
async def start_scraping_api_routes(req: Request, background_tasks: BackgroundTasks) -> ScrapingResponse:
    return await start_scraping(req, background_tasks)

@router.get("/api/routes/start-scraping")
async def start_scraping_api_routes_get(background_tasks: BackgroundTasks) -> ScrapingResponse:
    return await start_scraping_get(background_tasks)

@router.get("/scraping-progress/{task_id}")
async def get_scraping_progress(task_id: str) -> ScrapingProgress:
    """Get scraping progress for a task"""
    return scraping_tasks.get(task_id, ScrapingProgress(status=ScrapingStatus.FAILED))

@router.get("/scraping-results/{task_id}")
async def get_scraping_results(task_id: str) -> List[ScrapedProduct]:
    """Get scraping results for a completed task"""
    return scraping_results.get(task_id, [])


@router.get("/runs/{task_id}/export.csv")
async def export_run_csv(task_id: str):
    """Export all rows for a run from Google Sheets history as CSV."""
    import csv
    import io
    from app.libs.database import get_run_rows

    rows = await get_run_rows(task_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "store_name","product_id","title","price","currency","brand","description","image_url",
        "product_url","in_stock","scraped_at","match_score","match_confidence","match_reasoning"
    ])
    for r in rows:
        writer.writerow([
            r.get("store_name",""), r.get("product_id",""), r.get("title",""), r.get("price",""), r.get("currency",""), r.get("brand",""),
            r.get("description",""), r.get("image_url",""), r.get("product_url",""), r.get("in_stock",""), r.get("scraped_at",""),
            r.get("match_score",""), r.get("match_confidence",""), r.get("match_reasoning","")
        ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={task_id}.csv"})

# Compatibility for /api/routes/* forms
@router.get("/api/routes/scraping-progress/{task_id}")
async def get_scraping_progress_api_routes(task_id: str) -> ScrapingProgress:
    return await get_scraping_progress(task_id)

@router.get("/api/routes/scraping-results/{task_id}")
async def get_scraping_results_api_routes(task_id: str) -> List[ScrapedProduct]:
    return await get_scraping_results(task_id)


@router.get("/load-target-products")
async def load_target_products() -> Dict[str, Any]:
    """Read the catalog CSV and prepare canonical scraping terms and slot assignments.

    - Reads `Dzukou_Pricing_Overview_With_Names - Copy.csv` from repo root
    - Classifies each item into one of the provided slots, when possible
    - Derives a canonical search term per item (e.g., "Woodland Mouse Phone Stand" -> "phone stand")
    - Exports a categorized CSV to `product_data/catalog_categorized.csv`
    - Returns a de-duplicated list of canonical search terms
    """
    items = _read_catalog_csv()
    # Export categorized snapshot for transparency
    try:
        path = _export_catalog_assignment(items)
        print(f"Catalog categorized CSV exported to {path}")
    except Exception as e:
        print(f"Failed to export catalog categorization: {e}")

    terms = []
    seen = set()
    for it in items:
        term = (it.canonical_term or "").strip()
        if not term:
            continue
        if term not in seen:
            seen.add(term)
            terms.append(term)
    return {"targets": terms, "count": len(terms)}


@router.get("/export-catalog-csvs")
async def export_catalog_csvs() -> Dict[str, Any]:
    """Create different CSVs for each slot and each canonical term from the catalog file.

    Outputs:
    - product_data/catalog_categorized.csv (full table)
    - product_data/catalog_by_slot/<slot>.csv (one per slot)
    - product_data/catalog_by_term/<term>.csv (one per canonical term)
    """
    items = _read_catalog_csv()
    assignment_path = _export_catalog_assignment(items)
    by_slot = _export_catalog_per_slot(items)
    by_term = _export_catalog_per_term(items)

    return {
        "categorized_csv": str(assignment_path),
        "by_slot": {k: str(v) for k, v in by_slot.items()},
        "by_term": {k: str(v) for k, v in by_term.items()},
    }
