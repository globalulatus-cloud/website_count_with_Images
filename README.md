# 🎯 Ulatus Website Counter Tool

Professional website content and image analysis tool for translation services.

## Features

✅ **Single & Multiple Page Analysis**
- Analyze one or multiple URLs at once
- Word/character counting based on language
- CJK (Chinese, Japanese, Korean) character detection
- Latin-based word counting

✅ **Full Website Crawler**
- Sitemap.xml parsing for complete coverage
- Recursive link discovery with depth control
- Configurable max pages limit
- External link following option

✅ **Image Analysis**
- Total image count per page
- Alt text detection (accessibility)
- Title attribute detection
- Data attribute analysis
- CSS background image detection

✅ **Professional Reports**
- Detailed analysis tables
- CSV export functionality
- Accessibility warnings
- Real-time progress tracking

## Installation
```bash
# Clone the repository
git clone <https://github.com/globalulatus-cloud/website_count_with_Images>
cd ulatus-website-counter

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

## Deployment on Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Deploy!

## Usage

### Single Page Analysis
1. Enter one or more URLs (one per line)
2. Click "Analyze Content"
3. View results and download CSV

### Full Website Crawl
1. Enter website home URL
2. Configure max pages and depth
3. Click "Start Crawl"
4. Download comprehensive report

## Technology Stack

- **Frontend**: Streamlit
- **Web Scraping**: BeautifulSoup4, aiohttp
- **Data Processing**: Pandas
- **Async Processing**: asyncio

## License

© 2024 Ulatus. All rights reserved.
