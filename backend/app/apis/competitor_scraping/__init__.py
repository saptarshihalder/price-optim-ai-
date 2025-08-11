



from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
import time
from dataclasses import dataclass
from enum import Enum
import json
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
from app.libs.product_matcher import create_product_matcher, ProductMatch

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
    match_score: Optional[float] = None
    match_confidence: Optional[str] = None
    match_reasoning: Optional[str] = None
    raw_data: Dict[str, Any] = {}

class ScrapingProgress(BaseModel):
    status: ScrapingStatus
    current_store: Optional[str] = None
    completed_stores: int = 0
    total_stores: int = 0
    products_found: int = 0
    errors: List[str] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ScrapingRequest(BaseModel):
    target_products: List[str]  # Product names to search for
    max_products_per_store: int = 15

class ScrapingResponse(BaseModel):
    task_id: str
    status: ScrapingStatus
    message: str

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
    
    async def scrape_product_page(self, url: str, store_name: str) -> Optional[ScrapedProduct]:
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
                
                # Extract brand if missing
                if not product.brand:
                    brand_patterns = [
                        r'["\']brand["\']\s*:\s*["\']([^"\']*)["\'']',
                        r'<meta[^>]*property=["\']product:brand["\'][^>]*content=["\']([^"\']*)["\'']',
                        r'class=["\'][^"\']*(brand|manufacturer)[^"\']*(["\']).+?>([^<]+)',
                    ]
                    for pattern in brand_patterns:
                        try:
                            match = re.search(pattern, html, re.IGNORECASE)
                            if match:
                                product.brand = match.group(-1).strip()  # Get last group
                                break
                        except (re.error, IndexError):
                            continue
                
                return product if product.title and (product.price or len(product.title) > 10) else None
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    async def search_store(self, store: StoreInfo, query: str, max_products: int, target_product: str) -> List[ScrapedProduct]:
        """Search for products in a specific store with enhanced matching"""
        products = []
        matcher = create_product_matcher()
        
        try:
            # Detect if Shopify
            is_shopify = await self.detect_shopify(store.base_url)
            
            # Build search URL with better query formatting
            search_query = query.replace(' ', '+').lower()
            search_url = f"{store.base_url}{store.search_path}?q={search_query}"
            
            await self.rate_limiters[store.name].acquire()
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    print(f"Search failed for {store.name}: status {response.status}")
                    return products
                
                html = await response.text()
                
                # Enhanced product URL extraction
                url_patterns = [
                    r'href=["\']([^"\']*/products?/[^"\']*)["\']',
                    r'href=["\']([^"\']*/items?/[^"\']*)["\']',
                    r'href=["\']([^"\']*/product/[^"\']*)["\']',
                    r'href=["\']([^"\']*/shop/[^"\']*)["\']',
                    r'<a[^>]*href=["\']([^"\']*/[^"\']*(product|item)[^"\']*)["\']',
                ]
                
                product_urls = set()
                for pattern in url_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for match in matches:
                        url = match if isinstance(match, str) else match[0]
                        if url.startswith('/'):
                            full_url = urljoin(store.base_url, url)
                        elif url.startswith('http'):
                            full_url = url
                        else:
                            continue
                            
                        # Filter out obvious non-product URLs
                        if any(skip in url.lower() for skip in ['cart', 'account', 'login', 'contact', 'about', 'blog', 'news', 'policy', 'terms', 'faq', 'support', 'help']):
                            continue
                        
                        # Also filter out image and asset URLs
                        if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif', '.svg', '.ico', '.css', '.js', '.pdf', '.zip']):
                            continue
                            
                        product_urls.add(full_url)
                        
                        if len(product_urls) >= max_products * 2:  # Get more URLs for better filtering
                            break
                    
                    if len(product_urls) >= max_products * 2:
                        break
                
                print(f"Found {len(product_urls)} potential product URLs for {store.name}")
                
                # Scrape individual products with matching
                scraped_count = 0
                for url in list(product_urls):
                    if scraped_count >= max_products:
                        break
                        
                    product = await self.scrape_product_page(url, store.name)
                    if product:
                        # Apply product matching
                        match_result = matcher.match_product(target_product, {
                            'title': product.title,
                            'brand': product.brand,
                            'description': product.description
                        })
                        
                        # Only include products with reasonable match scores
                        if match_result.similarity_score >= 0.1:  # Lower threshold for more results
                            product.match_score = match_result.similarity_score
                            product.match_confidence = match_result.confidence
                            product.match_reasoning = match_result.reasoning
                            products.append(product)
                            scraped_count += 1
                            
                            print(f"Matched product: {product.title[:50]}... (Score: {match_result.similarity_score:.2f})")
                        
                        # Add small delay between requests
                        await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"Error searching {store.name}: {e}")
        
        # Sort by match score
        products.sort(key=lambda p: p.match_score or 0, reverse=True)
        return products[:max_products]

async def scrape_competitors_background(task_id: str, request: ScrapingRequest):
    """Background task for scraping competitors"""
    progress = scraping_tasks[task_id]
    progress.status = ScrapingStatus.RUNNING
    progress.started_at = datetime.now()
    progress.total_stores = len(TARGET_STORES)
    
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
                    
                    progress.completed_stores += 1
                    progress.products_found += len(store_products)
                    print(f"Completed {store.name}: found {len(store_products)} products")
                    
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
        
        # Store results
        scraping_results[task_id] = all_products
        
        progress.status = ScrapingStatus.COMPLETED
        progress.completed_at = datetime.now()
        
    except Exception as e:
        progress.status = ScrapingStatus.FAILED
        progress.errors.append(f"Fatal error: {str(e)}")
        progress.completed_at = datetime.now()

@router.post("/start-scraping")
async def start_scraping(request: ScrapingRequest, background_tasks: BackgroundTasks) -> ScrapingResponse:
    """Start competitor price scraping"""
    task_id = f"scrape_{int(time.time())}"
    
    # Initialize progress tracking
    scraping_tasks[task_id] = ScrapingProgress(
        status=ScrapingStatus.PENDING,
        total_stores=len(TARGET_STORES)
    )
    
    # Start background task
    background_tasks.add_task(scrape_competitors_background, task_id, request)
    
    return ScrapingResponse(
        task_id=task_id,
        status=ScrapingStatus.PENDING,
        message="Scraping task started successfully"
    )

@router.get("/scraping-progress/{task_id}")
async def get_scraping_progress(task_id: str) -> ScrapingProgress:
    """Get scraping progress for a task"""
    return scraping_tasks.get(task_id, ScrapingProgress(status=ScrapingStatus.FAILED))

@router.get("/scraping-results/{task_id}")
async def get_scraping_results(task_id: str) -> List[ScrapedProduct]:
    """Get scraping results for a completed task"""
    return scraping_results.get(task_id, [])
