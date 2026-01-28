import streamlit as st
import asyncio
import pandas as pd
from io import StringIO
from logic.scraper import fetch_website_text
from logic.counter import count_stats
from logic.crawler import crawl_site
from logic.vocabulary_analyzer import analyze_vocabulary, get_repetition_details
from logic.tm_analyzer import analyze_repetitions

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

# --- SESSION STATE INITIALIZATION ---
if 'crawl_results' not in st.session_state:
    st.session_state.crawl_results = None
if 'single_results' not in st.session_state:
    st.session_state.single_results = None
if 'analyzed_urls' not in st.session_state:
    st.session_state.analyzed_urls = []

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
                
                # Store in session state
                st.session_state.single_results = results
                st.session_state.analyzed_urls = urls
    
    # Display results if they exist in session state
    if st.session_state.single_results:
        results = st.session_state.single_results
        
        # Calculate totals from stored results
        total_count = sum(r['Word Count'] for r in results if isinstance(r['Word Count'], (int, float)))
        total_images = sum(r['Images'] for r in results if isinstance(r['Images'], (int, float)))
        total_images_without_alt = sum(r['Missing Alt'] for r in results if isinstance(r['Missing Alt'], (int, float)))
        
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
        st.dataframe(df, width="stretch")
        
        # Image Details Section
        if st.checkbox("📸 Show Detailed Image Analysis", value=False, key="show_images_single"):
            st.write("### Complete Image Inventory")
            
            all_images = []
            for url in st.session_state.analyzed_urls:
                try:
                    from logic.scraper import get_image_details_from_url
                    img_details = asyncio.run(get_image_details_from_url(url))
                    
                    for img in img_details:
                        all_images.append({
                            "Page URL": url,
                            "Image URL": img['src'],
                            "Alt Text": img['alt'] or "❌ Missing",
                            "Title": img['title'] or "-",
                            "Has Metadata": "✅" if img['has_metadata'] else "❌",
                            "Data Attributes": ", ".join(img['data_attributes']) if img['data_attributes'] else "-"
                        })
                except Exception as e:
                    st.warning(f"Could not fetch image details for {url}: {str(e)}")
            
            if all_images:
                df_images = pd.DataFrame(all_images)
                st.dataframe(df_images, width="stretch")
                
                # CSV Export for Images
                csv_images = df_images.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Image Details CSV",
                    data=csv_images,
                    file_name="ulatus_image_inventory.csv",
                    mime="text/csv",
                    key="download_images_single"
                )
            else:
                st.info("No images found on the analyzed pages.")
        
        # Page CSV Export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV Report",
            data=csv,
            file_name="ulatus_linguistic_report.csv",
            mime="text/csv",
            key="download_single"
        )
        
        # Vocabulary Analysis Section
        if st.checkbox("📊 Show Vocabulary Analysis", value=False, key="show_vocab_single"):
            st.write("### Vocabulary Analysis")
            
            # Combine all text from analyzed pages
            combined_text = ""
            for url in st.session_state.analyzed_urls:
                try:
                    text = asyncio.run(fetch_website_text(url))
                    combined_text += " " + text
                except:
                    pass
            
            if combined_text.strip():
                vocab_stats = analyze_vocabulary(combined_text)
                
                # Display language type
                lang_type = vocab_stats.get('language_type', 'Unknown')
                unit = vocab_stats.get('unit', 'words')
                st.info(f"📝 Language Type: **{lang_type}** | Analyzing: **{unit}**")
                
                # Vocabulary Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Total {unit.title()}</div><div class="metric-value">{vocab_stats["total_words"]:,}</div></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Unique {unit.title()}</div><div class="metric-value">{vocab_stats["unique_words"]:,}</div></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Repeated {unit.title()}</div><div class="metric-value">{vocab_stats["repeated_words"]:,}</div></div>', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Vocabulary Richness</div><div class="metric-value">{vocab_stats["vocabulary_richness"]}%</div></div>', unsafe_allow_html=True)
                
                # Most Common Words/Characters
                st.write(f"#### Top 20 Most Common {unit.title()}")
                common_words_data = [
                    {f"{unit.title()[:-1] if unit.endswith('s') else unit.title()}": word, "Occurrences": count, "Repetitions": count - 1}
                    for word, count in vocab_stats['most_common_words']
                ]
                df_common = pd.DataFrame(common_words_data)
                st.dataframe(df_common, width="stretch")
                
                # Detailed Repetitions (words appearing 5+ times)
                st.write(f"#### {unit.title()} Repeated 5+ Times")
                repetition_details = get_repetition_details(combined_text, min_repetitions=5)
                if repetition_details:
                    df_repetitions = pd.DataFrame(repetition_details)
                    st.dataframe(df_repetitions, width="stretch")
                    
                    # CSV Export for Vocabulary
                    csv_vocab = df_repetitions.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Vocabulary Analysis CSV",
                        data=csv_vocab,
                        file_name="ulatus_vocabulary_analysis.csv",
                        mime="text/csv",
                        key="download_vocab_single"
                    )
                else:
                    st.info(f"No {unit} repeated 5 or more times.")
            else:
                st.warning("No text content available for vocabulary analysis.")
        
        # TM-Style Repetition Analysis Section
        if st.checkbox("🔄 Show Translation Memory Analysis (Repetitions)", value=False, key="show_tm_single"):
            st.write("### Translation Memory Analysis")
            st.info("💡 Analyzes segments (sentences) to identify repetitions and unique content.")
            
            # Combine all text from analyzed pages
            combined_text = ""
            for url in st.session_state.analyzed_urls:
                try:
                    text = asyncio.run(fetch_website_text(url))
                    combined_text += " " + text
                except:
                    pass
            
            if combined_text.strip():
                with st.spinner("Analyzing repetitions..."):
                    tm_results = analyze_repetitions(combined_text)
                
                # Display language type
                lang_type = tm_results.get('language_type', 'UNKNOWN')
                unit = tm_results.get('unit', 'words')
                st.info(f"📝 Language Type: **{lang_type}** | Counting: **{unit}**")
                
                # Simple 3-metric display
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Total Count</div>
                        <div class="metric-value">{tm_results["total_words"]:,}</div>
                        <div class="metric-label" style="font-size: 0.65rem; margin-top: 0.5rem;">{tm_results["total_segments"]:,} segments • {unit}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="metric-card" style="background-color: #fee2e2;">
                        <div class="metric-label">Repetitions</div>
                        <div class="metric-value">{tm_results["repetition_words"]:,}</div>
                        <div class="metric-label" style="font-size: 0.65rem; margin-top: 0.5rem;">{tm_results["repeated_segments"]:,} segments • {unit}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="metric-card" style="background-color: #d1fae5;">
                        <div class="metric-label">Unique</div>
                        <div class="metric-value">{tm_results["unique_words"]:,}</div>
                        <div class="metric-label" style="font-size: 0.65rem; margin-top: 0.5rem;">{tm_results["unique_segments"]:,} segments • {unit}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detailed Repetition Table
                st.write("#### Repeated Segments")
                if tm_results['repetition_details']:
                    rep_data = []
                    for detail in tm_results['repetition_details'][:50]:  # Show top 50
                        rep_data.append({
                            'Segment': detail['segment'],
                            'Occurrences': detail['occurrences'],
                            f'{unit.title()}/Segment': detail['words_per_segment'],
                            f'Total {unit.title()}': detail['total_words']
                        })
                    
                    df_tm = pd.DataFrame(rep_data)
                    st.dataframe(df_tm, width="stretch")
                    
                    # CSV Export for TM Analysis
                    csv_tm = df_tm.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Repetition Analysis CSV",
                        data=csv_tm,
                        file_name="ulatus_repetition_analysis.csv",
                        mime="text/csv",
                        key="download_tm_single"
                    )
                else:
                    st.info("No repetitions found.")
            else:
                st.warning("No text content available for TM analysis.")

with tab2:
    root_url = st.text_input(
        "Enter website home URL",
        placeholder="https://example.com"
    )
    
    st.info("ℹ️ This will crawl the **entire website** - all pages will be analyzed automatically.")
    
    with st.expander("⚙️ Advanced Options (Optional)"):
        max_depth = st.number_input(
            "Max crawl depth",
            min_value=1,
            value=10,
            step=1,
            help="How many levels deep to follow links (default: 10 - sufficient for most websites)"
        )
        
        follow_external = st.checkbox(
            "Follow external links",
            value=False,
            help="Crawl links outside the main domain"
        )
    
    if st.button("🚀 Start Complete Website Crawl", key="analyze_crawl"):
        if not root_url.strip():
            st.error("Please enter a website URL")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Crawling Entire Website... This may take a few minutes for large sites."):
                try:
                    status_text.text("Starting complete website crawl...")
                    crawl_results = cached_crawl(
                        root_url,
                        None,  # No max_pages limit - crawl everything
                        max_depth,
                        follow_external
                    )
                    progress_bar.progress(100)
                    
                    # Store in session state
                    st.session_state.crawl_results = crawl_results
                    
                except Exception as e:
                    st.error(f"Crawling failed: {str(e)}")
                    st.info("Try reducing the crawl depth or check if the website is accessible.")
    
    # Display results if they exist
    if st.session_state.crawl_results:
        crawl_results = st.session_state.crawl_results
        
        if not crawl_results:
            st.warning("No pages found or analysis failed.")
        else:
            st.success(f"✅ Successfully crawled {len(crawl_results)} pages!")
            
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
            st.dataframe(df_crawl, width="stretch")
            
            # Image Details Section
            if st.checkbox("📸 Show Detailed Image Analysis", value=False):
                st.write("### Complete Image Inventory")
                
                all_images = []
                for res in crawl_results:
                    page_url = res['url']
                    img_details = res.get('image_stats', {}).get('image_details', [])
                    
                    for img in img_details:
                        all_images.append({
                            "Page URL": page_url,
                            "Image URL": img['src'],
                            "Alt Text": img['alt'] or "❌ Missing",
                            "Title": img['title'] or "-",
                            "Has Metadata": "✅" if img['has_metadata'] else "❌",
                            "Data Attributes": ", ".join(img['data_attributes']) if img['data_attributes'] else "-"
                        })
                
                if all_images:
                    df_images = pd.DataFrame(all_images)
                    st.dataframe(df_images, width="stretch")
                    
                    # CSV Export for Images
                    csv_images = df_images.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Image Details CSV",
                        data=csv_images,
                        file_name="ulatus_image_inventory.csv",
                        mime="text/csv",
                        key="download_images"
                    )
                else:
                    st.info("No images found on the crawled pages.")
            
            # CSV Export
            csv_crawl = df_crawl.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Full Crawl Report",
                data=csv_crawl,
                file_name="ulatus_crawl_report.csv",
                mime="text/csv",
                key="download_crawl"
            )
            
            # Vocabulary Analysis Section
            if st.checkbox("📊 Show Vocabulary Analysis", value=False, key="show_vocab_crawl"):
                st.write("### Vocabulary Analysis - Entire Website")
                
                # Combine all text from crawled pages
                combined_text = ""
                for res in crawl_results:
                    # Extract text from stats or re-fetch
                    try:
                        # Use cached text if available in results
                        # Otherwise we'll need to work with what we have
                        url = res['url']
                        text = asyncio.run(fetch_website_text(url))
                        combined_text += " " + text
                    except:
                        pass
                
                if combined_text.strip():
                    vocab_stats = analyze_vocabulary(combined_text)
                    
                    # Display language type
                    lang_type = vocab_stats.get('language_type', 'Unknown')
                    unit = vocab_stats.get('unit', 'words')
                    st.info(f"📝 Language Type: **{lang_type}** | Analyzing: **{unit}**")
                    
                    # Vocabulary Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f'<div class="metric-card"><div class="metric-label">Total {unit.title()}</div><div class="metric-value">{vocab_stats["total_words"]:,}</div></div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="metric-card"><div class="metric-label">Unique {unit.title()}</div><div class="metric-value">{vocab_stats["unique_words"]:,}</div></div>', unsafe_allow_html=True)
                    with col3:
                        st.markdown(f'<div class="metric-card"><div class="metric-label">Repeated {unit.title()}</div><div class="metric-value">{vocab_stats["repeated_words"]:,}</div></div>', unsafe_allow_html=True)
                    with col4:
                        st.markdown(f'<div class="metric-card"><div class="metric-label">Vocabulary Richness</div><div class="metric-value">{vocab_stats["vocabulary_richness"]}%</div></div>', unsafe_allow_html=True)
                    
                    # Most Common Words/Characters
                    st.write(f"#### Top 20 Most Common {unit.title()} Across All Pages")
                    common_words_data = [
                        {f"{unit.title()[:-1] if unit.endswith('s') else unit.title()}": word, "Occurrences": count, "Repetitions": count - 1}
                        for word, count in vocab_stats['most_common_words']
                    ]
                    df_common = pd.DataFrame(common_words_data)
                    st.dataframe(df_common, width="stretch")
                    
                    # Detailed Repetitions (words appearing 10+ times for large sites)
                    st.write(f"#### {unit.title()} Repeated 10+ Times")
                    repetition_details = get_repetition_details(combined_text, min_repetitions=10)
                    if repetition_details:
                        df_repetitions = pd.DataFrame(repetition_details)
                        st.dataframe(df_repetitions, width="stretch")
                        
                        # CSV Export for Vocabulary
                        csv_vocab = df_repetitions.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Vocabulary Analysis CSV",
                            data=csv_vocab,
                            file_name="ulatus_vocabulary_analysis.csv",
                            mime="text/csv",
                            key="download_vocab_crawl"
                        )
                    else:
                        st.info(f"No {unit} repeated 10 or more times.")
                else:
                    st.warning("No text content available for vocabulary analysis.")
            
            # TM-Style Repetition Analysis Section for Full Crawl
            if st.checkbox("🔄 Show Translation Memory Analysis (Repetitions)", value=False, key="show_tm_crawl"):
                st.write("### Translation Memory Analysis - Entire Website")
                st.info("💡 Analyzes segments (sentences) across all pages to identify repetitions and unique content.")
                
                # Combine all text from crawled pages
                combined_text = ""
                for res in crawl_results:
                    try:
                        url = res['url']
                        text = asyncio.run(fetch_website_text(url))
                        combined_text += " " + text
                    except:
                        pass
                
                if combined_text.strip():
                    with st.spinner("Analyzing repetitions across entire website..."):
                        tm_results = analyze_repetitions(combined_text)
                    
                    # Display language type
                    lang_type = tm_results.get('language_type', 'UNKNOWN')
                    unit = tm_results.get('unit', 'words')
                    st.info(f"📝 Language Type: **{lang_type}** | Counting: **{unit}**")
                    
                    # Simple 3-metric display
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Total Count</div>
                            <div class="metric-value">{tm_results["total_words"]:,}</div>
                            <div class="metric-label" style="font-size: 0.65rem; margin-top: 0.5rem;">{tm_results["total_segments"]:,} segments • {unit}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div class="metric-card" style="background-color: #fee2e2;">
                            <div class="metric-label">Repetitions</div>
                            <div class="metric-value">{tm_results["repetition_words"]:,}</div>
                            <div class="metric-label" style="font-size: 0.65rem; margin-top: 0.5rem;">{tm_results["repeated_segments"]:,} segments • {unit}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"""
                        <div class="metric-card" style="background-color: #d1fae5;">
                            <div class="metric-label">Unique</div>
                            <div class="metric-value">{tm_results["unique_words"]:,}</div>
                            <div class="metric-label" style="font-size: 0.65rem; margin-top: 0.5rem;">{tm_results["unique_segments"]:,} segments • {unit}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Detailed Repetition Table
                    st.write("#### Repeated Segments Across Website")
                    repetition_percentage = (tm_results["repetition_words"] / tm_results["total_words"] * 100) if tm_results["total_words"] > 0 else 0
                    st.write(f"📊 Repetition rate: **{repetition_percentage:.1f}%** of total content")
                    
                    if tm_results['repetition_details']:
                        rep_data = []
                        for detail in tm_results['repetition_details'][:100]:  # Show top 100
                            rep_data.append({
                                'Segment': detail['segment'],
                                'Occurrences': detail['occurrences'],
                                f'{unit.title()}/Segment': detail['words_per_segment'],
                                f'Total {unit.title()}': detail['total_words']
                            })
                        
                        df_tm = pd.DataFrame(rep_data)
                        st.dataframe(df_tm, width="stretch")
                        
                        # CSV Export for TM Analysis
                        csv_tm = df_tm.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Repetition Analysis CSV",
                            data=csv_tm,
                            file_name="ulatus_repetition_analysis.csv",
                            mime="text/csv",
                            key="download_tm_crawl"
                        )
                    else:
                        st.info("No repetitions found.")
                else:
                    st.warning("No text content available for TM analysis.")

# --- FOOTER ---
st.markdown("---")
st.markdown("Made with ❤️ by Ulatus | Professional Translation Services")
