import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict, Optional
import xml.etree.ElementTree as ET
from logic.counter import count_stats

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
                async with session.get(sitemap_url, timeout=10) as response:
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
                        
                        print(f"Found {len(sitemap_urls)} URLs in sitemap")
                        break
            except Exception as e:
                print(f"Could not fetch sitemap {sitemap_url}: {e}")
                continue
        
        return sitemap_urls
    
    async def fetch_sitemap_file(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        """Fetch a specific sitemap file"""
        urls = set()
        try:
            async with session.get(url, timeout=10) as response:
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
        """Crawl a single page and extract links"""
        if url in self.visited_urls or depth > self.max_depth:
            return [], None
        
        if self.max_pages and len(self.visited_urls) >= self.max_pages:
            return [], None
        
        self.visited_urls.add(url)
        
        try:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    print(f"Failed to fetch {url}: Status {response.status}")
                    return [], None
                
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
                
                # Extract links for further crawling
                links = []
                for link in soup.find_all('a', href=True):
                    absolute_url = urljoin(url, link['href'])
                    # Clean URL (remove fragments)
                    absolute_url = absolute_url.split('#')[0]
                    if self.is_valid_url(absolute_url) and absolute_url not in self.visited_urls:
                        links.append(absolute_url)
                
                return links, result
                
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return [], None
    
    async def crawl(self):
        """Main crawl function with BFS approach"""
        async with aiohttp.ClientSession() as session:
            # Try to get sitemap first
            sitemap_urls = await self.fetch_sitemap(session)
            
            # Start with root URL and sitemap URLs
            queue = [(self.root_url, 0)]
            
            # Add sitemap URLs with depth 0
            for url in sitemap_urls:
                if self.is_valid_url(url):
                    queue.append((url, 0))
            
            while queue:
                # Limit concurrent requests
                batch = queue[:10]  # Process 10 URLs at a time
                queue = queue[10:]
                
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
                    break
                
                # Progress feedback
                print(f"Crawled {len(self.visited_urls)} pages, {len(queue)} in queue")
        
        return self.results

async def crawl_site(root_url: str, max_pages: Optional[int] = None, 
                    max_depth: int = 5, follow_external: bool = False) -> List[Dict]:
    """
    Enhanced crawler that:
    1. Parses sitemap.xml for complete URL list
    2. Follows links recursively with depth control
    3. Analyzes images and metadata
    4. Respects max_pages limit
    """
    crawler = EnhancedWebsiteCrawler(root_url, max_pages, max_depth, follow_external)
    results = await crawler.crawl()
    return results
