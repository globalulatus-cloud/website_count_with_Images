import streamlit as st
import asyncio
import pandas as pd
from io import StringIO
from logic.scraper import fetch_website_text
from logic.counter import count_stats
from logic.crawler import crawl_site

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Ulatus Website Counter Tool",
    page_icon="🎯",
    layout="centered"
)

# --- CUSTOM CSS (Crimson Ulatus Branding) ---
st.markdown("""
<style>
    :root {
        --brand-crimson: #B4252D;
    }
    .main {
        background-color: #fdfdfd;
    }
    h1 {
        color: var(--brand-crimson) !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .stButton>button {
        background-color: var(--brand-crimson);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        border: none;
    }
    .stButton>button:hover {
        background-color: #9c1f27;
        color: white;
        border: none;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
        color: #6b7280;
    }
    .stTabs [aria-selected="true"] {
        color: var(--brand-crimson) !important;
        border-bottom-color: var(--brand-crimson) !important;
    }
    .metric-card {
        background-color: #f9fafb;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        text-align: center;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #6b7280;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a1a;
    }
    .warning-box {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("Ulatus Website Counter Tool")
st.write("Professional Website Content & Image Analysis")

# --- CACHING FOR PERFORMANCE ---
@st.cache_data(ttl=3600)
def cached_crawl(root_url, max_pages, max_depth, follow_external):
    return asyncio.run(crawl_site(root_url, max_pages, max_depth, follow_external))

# --- APP LOGIC ---
tab1, tab2 = st.tabs(["Single & Multiple Pages", "Full Website Crawler"])

with tab1:
    urls_input = st.text_area(
        "Enter URLs here (one per line)",
        placeholder="https://example.com\nhttps://ulatus.com",
        height=150
    )
    
    if st.button("Analyze Content", key="analyze_single"):
        urls = [u.strip() for u in urls_input.split('\n') if u.strip()]
        if not urls:
            st.error("Please enter at least one URL")
        else:
            with st.spinner("Analyzing Content..."):
                results = []
                total_count = 0
                total_images = 0
                total_images_without_alt = 0
                
                for url in urls:
                    try:
                        text = asyncio.run(fetch_website_text(url))
                        stats = count_stats(text)
                        
                        # Get image stats from scraper
                        from logic.scraper import analyze_images_from_url
                        image_stats = asyncio.run(analyze_images_from_url(url))
                        
                        results.append({
                            "URL": url,
                            "Title": url,
                            "Word Count": stats['count'],
                            "Type": stats['type'].upper(),
                            "Group": stats['language_group'],
                            "Images": image_stats['total_images'],
                            "Missing Alt": image_stats['images_without_alt']
                        })
                        total_count += stats['count']
                        total_images += image_stats['total_images']
                        total_images_without_alt += image_stats['images_without_alt']
                    except Exception as e:
                        results.append({
                            "URL": url,
                            "Title": "Fetch Failed",
                            "Word Count": 0,
                            "Type": "-",
                            "Group": f"Error: {str(e)}",
                            "Images": 0,
                            "Missing Alt": 0
                        })
                
                # Summary Columns
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Total Words</div><div class="metric-value">{total_count:,}</div></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Pages</div><div class="metric-value">{len(results)}</div></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Total Images</div><div class="metric-value">{total_images}</div></div>', unsafe_allow_html=True)
                with col4:
                    primary_group = results[0]['Group'] if results and 'Error' not in str(results[0]['Group']) else "-"
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Primary Mode</div><div class="metric-value">{primary_group}</div></div>', unsafe_allow_html=True)
                
                # Accessibility Warning
                if total_images_without_alt > 0:
                    st.markdown(f'<div class="warning-box">⚠️ <strong>Accessibility Issue:</strong> {total_images_without_alt} images missing alt text</div>', unsafe_allow_html=True)
                
                st.write("### Detailed Analysis")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                # CSV Export
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV Report",
                    data=csv,
                    file_name="ulatus_linguistic_report.csv",
                    mime="text/csv",
                    key="download_single"
                )

with tab2:
    root_url = st.text_input(
        "Enter website home URL",
        placeholder="https://example.com"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        max_pages = st.number_input(
            "Max pages to crawl (0 = unlimited)",
            min_value=0,
            value=100,
            step=10,
            help="Recommended: 100-500 for faster results"
        )
    with col2:
        max_depth = st.number_input(
            "Max crawl depth",
            min_value=1,
            value=5,
            step=1,
            help="How many levels deep to follow links"
        )
    
    follow_external = st.checkbox(
        "Follow external links",
        value=False,
        help="Crawl links outside the main domain"
    )
    
    if st.button("🚀 Start Crawl", key="analyze_crawl"):
        if not root_url.strip():
            st.error("Please enter a website URL")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Crawling Website..."):
                try:
                    status_text.text("Starting crawl...")
                    crawl_results = cached_crawl(
                        root_url,
                        max_pages if max_pages > 0 else None,
                        max_depth,
                        follow_external
                    )
                    progress_bar.progress(100)
                    
                    if not crawl_results:
                        st.warning("No pages found or analysis failed.")
                    else:
                        status_text.text(f"✅ Successfully crawled {len(crawl_results)} pages!")
                        
                        # Aggregation
                        total_count = sum(r['stats']['count'] for r in crawl_results)
                        total_images = sum(r.get('image_stats', {}).get('total_images', 0) for r in crawl_results)
                        total_images_without_alt = sum(r.get('image_stats', {}).get('images_without_alt', 0) for r in crawl_results)
                        primary_group = "CJK" if any(r['stats']['language_group'] == "CJK" for r in crawl_results) else "Latin"
                        
                        # Summary Columns
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.markdown(f'<div class="metric-card"><div class="metric-label">Total Words</div><div class="metric-value">{total_count:,}</div></div>', unsafe_allow_html=True)
                        with col2:
                            st.markdown(f'<div class="metric-card"><div class="metric-label">Pages Crawled</div><div class="metric-value">{len(crawl_results)}</div></div>', unsafe_allow_html=True)
                        with col3:
                            st.markdown(f'<div class="metric-card"><div class="metric-label">Total Images</div><div class="metric-value">{total_images}</div></div>', unsafe_allow_html=True)
                        with col4:
                            st.markdown(f'<div class="metric-card"><div class="metric-label">Primary Mode</div><div class="metric-value">{primary_group}</div></div>', unsafe_allow_html=True)
                        
                        # Accessibility Warning
                        if total_images_without_alt > 0:
                            accessibility_pct = round((total_images_without_alt / total_images * 100) if total_images > 0 else 0, 1)
                            st.markdown(f'<div class="warning-box">⚠️ <strong>Accessibility Issue:</strong> {total_images_without_alt} images ({accessibility_pct}%) missing alt text</div>', unsafe_allow_html=True)
                        
                        # Detailed Results
                        st.write("### Detailed Analysis")
                        flattened_results = []
                        for res in crawl_results:
                            img_stats = res.get('image_stats', {})
                            flattened_results.append({
                                "URL": res['url'],
                                "Title": res['title'],
                                "Word Count": res['stats']['count'],
                                "Type": res['stats']['type'].upper(),
                                "Group": res['stats']['language_group'],
                                "Images": img_stats.get('total_images', 0),
                                "Missing Alt": img_stats.get('images_without_alt', 0),
                                "With Title": img_stats.get('images_with_title', 0)
                            })
                        
                        df_crawl = pd.DataFrame(flattened_results)
                        st.dataframe(df_crawl, use_container_width=True)
                        
                        # CSV Export
                        csv_crawl = df_crawl.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Full Crawl Report",
                            data=csv_crawl,
                            file_name="ulatus_crawl_report.csv",
                            mime="text/csv",
                            key="download_crawl"
                        )
                except Exception as e:
                    st.error(f"Crawling failed: {str(e)}")
                    st.info("Try reducing the max pages or check if the website is accessible.")

# --- FOOTER ---
st.markdown("---")
st.markdown("Made with ❤️ by Ulatus | Professional Translation Services")
