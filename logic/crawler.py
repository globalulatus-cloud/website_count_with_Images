# logic/crawler.py
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict, Optional
import xml.etree.ElementTree as ET
from logic.counter import count_stats
import ssl
import time

class EnhancedWebsiteCrawler:
    def __init__(self, root_url: str, max_pages: Optional[int] = None, 
                 max_depth: int = 5, follow_external: bool = False):
        self.root_url = root_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.follow_external = follow_external
        self.visited_urls: Set[str] = set()
        self.results: List[Dict] = []
        self.domain = urlparse(root_url).netloc
        self.errors: List[Dict] = []
        self.rate_limit_delay = 0.5  # Start with 0.5 second delay between requests
        self.consecutive_429s = 0
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        parsed = urlparse(url)
        
        # Skip non-http protocols
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Skip files we don't want to analyze
        skip_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', 
                          '.mp4', '.mp3', '.doc', '.docx', '.xls', '.xlsx',
                          '.css', '.js', '.ico', '.svg', '.woff', '.ttf']
        if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
            return False
        
        # Check domain restrictions
        if not self.follow_external and parsed.netloc != self.domain:
            return False
        
        return True
    
    async def fetch_sitemap(self, session: aiohttp.ClientSession) -> Set[str]:
        """Try to fetch and parse sitemap.xml"""
        sitemap_urls = set()
        sitemap_locations = [
            f"{self.root_url}/sitemap.xml",
            f"{self.root_url}/sitemap_index.xml",
            f"{self.root_url}/sitemap-index.xml"
        ]
        
        for sitemap_url in sitemap_locations:
            try:
                async with session.get(sitemap_url, timeout=10, ssl=False) as response:
                    if response.status == 200:
                        content = await response.text()
                        root = ET.fromstring(content)
                        
                        # Handle sitemap index
                        for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                            loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc is not None:
                                nested_urls = await self.fetch_sitemap_file(session, loc.text)
                                sitemap_urls.update(nested_urls)
                        
                        # Handle regular sitemap
                        for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                            loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc is not None:
                                sitemap_urls.add(loc.text)
                        
                        print(f"✓ Found {len(sitemap_urls)} URLs in sitemap")
                        break
            except Exception as e:
                print(f"Could not fetch sitemap {sitemap_url}: {e}")
                continue
        
        return sitemap_urls
    
    async def fetch_sitemap_file(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        """Fetch a specific sitemap file"""
        urls = set()
        try:
            async with session.get(url, timeout=10, ssl=False) as response:
                if response.status == 200:
                    content = await response.text()
                    root = ET.fromstring(content)
                    for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                        loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                        if loc is not None:
                            urls.add(loc.text)
        except Exception as e:
            print(f"Error fetching sitemap file {url}: {e}")
        return urls
    
    def analyze_images(self, soup: BeautifulSoup) -> Dict:
        """Analyze all images on the page"""
        images = soup.find_all('img')
        
        image_stats = {
            'total_images': len(images),
            'images_with_alt': 0,
            'images_without_alt': 0,
            'images_with_title': 0,
            'images_with_data_attrs': 0,
            'image_details': []
        }
        
        for img in images:
            alt = img.get('alt', '').strip()
            title = img.get('title', '').strip()
            src = img.get('src', '')
            
            # Check for data attributes
            data_attrs = [k for k in img.attrs.keys() if k.startswith('data-')]
            
            has_alt = bool(alt)
            has_title = bool(title)
            has_data = len(data_attrs) > 0
            
            if has_alt:
                image_stats['images_with_alt'] += 1
            else:
                image_stats['images_without_alt'] += 1
            
            if has_title:
                image_stats['images_with_title'] += 1
            
            if has_data:
                image_stats['images_with_data_attrs'] += 1
            
            image_stats['image_details'].append({
                'src': src,
                'alt': alt if has_alt else None,
                'title': title if has_title else None,
                'has_metadata': has_alt or has_title or has_data,
                'data_attributes': data_attrs
            })
        
        # Also check for CSS background images (basic detection)
        style_tags = soup.find_all('style')
        inline_styles = soup.find_all(style=True)
        bg_image_count = 0
        
        for style in style_tags:
            if style.string and ('background-image' in style.string or 'background:' in style.string):
                bg_image_count += style.string.count('url(')
        
        for elem in inline_styles:
            style_attr = elem.get('style', '')
            if 'background-image' in style_attr or 'background:' in style_attr:
                bg_image_count += style_attr.count('url(')
        
        image_stats['css_background_images'] = bg_image_count
        
        return image_stats
    
    async def crawl_page(self, session: aiohttp.ClientSession, url: str, depth: int) -> tuple:
        """Crawl a single page and extract links with rate limiting"""
        if url in self.visited_urls or depth > self.max_depth:
            return [], None
        
        if self.max_pages and len(self.visited_urls) >= self.max_pages:
            return [], None
        
        self.visited_urls.add(url)
        
        # Rate limiting delay
        await asyncio.sleep(self.rate_limit_delay)
        
        # Retry logic for 429 errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Enhanced request with better headers and SSL handling
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                async with session.get(
                    url, 
                    timeout=30,
                    ssl=False,
                    headers=headers,
                    allow_redirects=True
                ) as response:
                    if response.status == 429:
                        self.consecutive_429s += 1
                        # Exponential backoff
                        backoff_time = min(30, 2 ** attempt * 5)  # 5s, 10s, 20s (max 30s)
                        print(f"⚠️ Rate limited! Waiting {backoff_time}s before retry (attempt {attempt + 1}/{max_retries})...")
                        
                        # Increase global delay if we're getting too many 429s
                        if self.consecutive_429s > 5:
                            self.rate_limit_delay = min(3.0, self.rate_limit_delay * 1.5)
                            print(f"⚠️ Increasing rate limit delay to {self.rate_limit_delay:.1f}s")
                        
                        await asyncio.sleep(backoff_time)
                        continue  # Retry
                    
                    if response.status != 200:
                        error_msg = f"HTTP {response.status}"
                        print(f"✗ Failed to fetch {url}: {error_msg}")
                        self.errors.append({'url': url, 'error': error_msg})
                        return [], None
                    
                    # Success - reset consecutive 429 counter
                    self.consecutive_429s = 0
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract text content
                    for script in soup(["script", "style", "nav", "footer"]):
                        script.decompose()
                    text = soup.get_text(separator=' ', strip=True)
                    
                    # Get title
                    title = soup.title.string if soup.title else url
                    
                    # Count statistics
                    stats = count_stats(text)
                    
                    # Analyze images
                    image_stats = self.analyze_images(soup)
                    
                    # Store results
                    result = {
                        'url': url,
                        'title': title,
                        'stats': stats,
                        'image_stats': image_stats,
                        'depth': depth
                    }
                    
                    print(f"✓ Crawled: {url} (Depth: {depth}, Words: {stats['count']}, Images: {image_stats['total_images']})")
                    
                    # Extract links for further crawling
                    links = []
                    for link in soup.find_all('a', href=True):
                        absolute_url = urljoin(url, link['href'])
                        # Clean URL (remove fragments)
                        absolute_url = absolute_url.split('#')[0]
                        if self.is_valid_url(absolute_url) and absolute_url not in self.visited_urls:
                            links.append(absolute_url)
                    
                    return links, result
                    
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    print(f"⚠️ Timeout, retrying {url} (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(5)
                    continue
                error_msg = "Request timeout (30s)"
                print(f"✗ Timeout: {url}")
                self.errors.append({'url': url, 'error': error_msg})
                return [], None
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Connection error, retrying {url}...")
                    await asyncio.sleep(5)
                    continue
                error_msg = f"Connection error: {str(e)}"
                print(f"✗ Connection error for {url}: {str(e)}")
                self.errors.append({'url': url, 'error': error_msg})
                return [], None
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(f"✗ Error crawling {url}: {str(e)}")
                self.errors.append({'url': url, 'error': error_msg})
                return [], None
        
        # All retries failed
        error_msg = "Max retries exceeded"
        print(f"✗ Failed after {max_retries} retries: {url}")
        self.errors.append({'url': url, 'error': error_msg})
        return [], None
    
    async def crawl(self):
        """Main crawl function with BFS approach"""
        # Create SSL context that doesn't verify certificates
        connector = aiohttp.TCPConnector(ssl=False, limit=10)
        timeout = aiohttp.ClientTimeout(total=60, connect=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            print(f"\n🔍 Starting crawl of {self.root_url}...")
            
            # Try to get sitemap first
            print("📄 Checking for sitemap...")
            sitemap_urls = await self.fetch_sitemap(session)
            
            # Start with root URL and sitemap URLs
            queue = [(self.root_url, 0)]
            
            # Add sitemap URLs with depth 0
            for url in sitemap_urls:
                if self.is_valid_url(url):
                    queue.append((url, 0))
            
            print(f"📋 Queue initialized with {len(queue)} URLs")
            
            while queue:
                # Limit concurrent requests - REDUCED for better rate limiting
                batch = queue[:2]  # Only 2 concurrent requests to avoid rate limiting
                queue = queue[2:]
                
                tasks = [self.crawl_page(session, url, depth) for url, depth in batch]
                results = await asyncio.gather(*tasks)
                
                for links, result in results:
                    if result:
                        self.results.append(result)
                    
                    # Add new links to queue
                    for link in links:
                        if link not in [u for u, _ in queue]:
                            next_depth = result['depth'] + 1 if result else 1
                            queue.append((link, next_depth))
                
                # Check if we've hit max pages
                if self.max_pages and len(self.visited_urls) >= self.max_pages:
                    print(f"⚠️ Reached max pages limit ({self.max_pages})")
                    break
                
                # Progress feedback
                print(f"📊 Progress: {len(self.visited_urls)} pages crawled, {len(queue)} in queue")
        
        # Print summary
        print(f"\n✅ Crawl complete!")
        print(f"   Pages crawled: {len(self.results)}")
        print(f"   Errors: {len(self.errors)}")
        
        if self.errors:
            print(f"\n⚠️ Errors encountered:")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"   - {error['url']}: {error['error']}")
        
        return self.results

async def crawl_site(root_url: str, max_pages: Optional[int] = None, 
                    max_depth: int = 5, follow_external: bool = False) -> List[Dict]:
    """
    Enhanced crawler that:
    1. Parses sitemap.xml for complete URL list
    2. Follows links recursively with depth control
    3. Analyzes images and metadata
    4. Respects max_pages limit
    5. Better error handling and SSL support
    """
    crawler = EnhancedWebsiteCrawler(root_url, max_pages, max_depth, follow_external)
    results = await crawler.crawl()
    return results
