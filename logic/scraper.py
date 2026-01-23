import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, List
from urllib.parse import urljoin

async def fetch_website_text(url: str) -> str:
    """Fetch text content from a website"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=15) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch {url}: Status {response.status}")
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts, styles, navigation, footer
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text(separator=' ', strip=True)
            return text

async def analyze_images_from_url(url: str) -> Dict:
    """Fetch and analyze images from a specific URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=15) as response:
            if response.status != 200:
                return {
                    'total_images': 0,
                    'images_with_alt': 0,
                    'images_without_alt': 0,
                    'images_with_title': 0
                }
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            images = soup.find_all('img')
            
            image_stats = {
                'total_images': len(images),
                'images_with_alt': 0,
                'images_without_alt': 0,
                'images_with_title': 0
            }
            
            for img in images:
                alt = img.get('alt', '').strip()
                title = img.get('title', '').strip()
                
                if alt:
                    image_stats['images_with_alt'] += 1
                else:
                    image_stats['images_without_alt'] += 1
                
                if title:
                    image_stats['images_with_title'] += 1
            
            return image_stats

async def get_image_details_from_url(url: str) -> List[Dict]:
    """Fetch detailed image information including URLs from a specific page"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=15) as response:
            if response.status != 200:
                return []
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            images = soup.find_all('img')
            image_details = []
            
            for img in images:
                src = img.get('src', '')
                
                # Convert relative URLs to absolute URLs
                if src:
                    src = urljoin(url, src)
                
                alt = img.get('alt', '').strip()
                title = img.get('title', '').strip()
                
                # Check for data attributes
                data_attrs = [k for k in img.attrs.keys() if k.startswith('data-')]
                
                has_alt = bool(alt)
                has_title = bool(title)
                has_data = len(data_attrs) > 0
                
                image_details.append({
                    'src': src,
                    'alt': alt if has_alt else None,
                    'title': title if has_title else None,
                    'has_metadata': has_alt or has_title or has_data,
                    'data_attributes': data_attrs
                })
            
            return image_details
