import asyncio
import json
import os
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import streamlit as st
import pineconeDataLoad as pineconeDataLoad
 
 
def call_pinecone(fileName):
    st.write("📤 Uploading to Pinecone:", fileName)
    pineconeDataLoad.uploadFileOnPonecone(fileName)
    st.success("✅ Upload completed!")
 
 
async def scrape_to_json(base_url: str, output_file: str = "scraped_data.json", max_pages: int = 100):
    visited = set()
    to_visit = {base_url}
    results = {}
 
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
 
    exclude_urls = {
        "https://agrimine.in/wp-content/uploads/",
        "https://rajexim.com/clientele/"
    }
 
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,
                                          args=["--no-sandbox", "--disable-setuid-sandbox"]
                                          )
         #   args=["--start-maximized"]
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            java_script_enabled=True
        )
 
        page = await context.new_page()
 
        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """)
 
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
 
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop()
            if url in visited:
                continue
            visited.add(url)
 
            # Skip explicitly excluded URLs
            if any(url.startswith(excluded) for excluded in exclude_urls):
                st.write(f"⏭️ Skipping excluded URL: {url}")
                continue
 
            try:
                st.write(f"🔍 Scraping: {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(3)
 
                try:
                    close_popup = await page.query_selector(
                        "button[class*='popup-close'], .close, .close-popup, .login-close"
                    )
                    if close_popup:
                        await close_popup.click()
                        await asyncio.sleep(1)
                        st.write("🔒 Popup closed")
                except Exception as e:
                    st.warning(f"Popup close failed: {e}")
 
                await asyncio.sleep(3)
 
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                results[url] = text
 
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)
                    parsed = urlparse(full_url)
 
                    # Skip excluded URLs in links
                    if any(full_url.startswith(excluded) for excluded in exclude_urls):
                        continue
 
                    if parsed.netloc.endswith(base_domain) and parsed.scheme in ["http", "https"]:
                        if full_url not in visited:
                            to_visit.add(full_url)
 
            except Exception as e:
                st.error(f"❌ Failed to scrape {url}: {e}")
                results[url] = f"Failed to scrape: {str(e)}"
 
        await browser.close()
 
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
 
    st.success(f"✅ Saved {len(results)} pages to {output_file}")
 
 
# 🚀 Streamlit UI logic
def main():
    st.set_page_config(page_title="Web Scraper", layout="centered")
    st.title("🌐 Website Scraper & Pinecone Uploader")
 
    # -- Session state setup
    if "scraped" not in st.session_state:
        st.session_state.scraped = False
 
    url_input = st.text_input("🔗 Enter URL to scrape:", value="https://example.com")
    max_pages = st.slider("📄 Max pages to scrape:", min_value=10, max_value=200, value=50)
 
    if st.button("🕸️ Scrape Website"):
        if not url_input:
            st.error("❌ Please enter a valid URL!")
        else:
            st.info("🔄 Scraping started...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(scrape_to_json(url_input, "scraped_data.json", max_pages))
            st.session_state.scraped = True
            st.success("✅ Scraping completed.")
 
    # -- JSON Preview
    if os.path.exists("scraped_data.json"):
        st.markdown("### 📄 Preview of Scraped Data")
        with open("scraped_data.json", "r", encoding="utf-8") as f:
            try:
                scraped = json.load(f)
                st.json(scraped)
            except Exception as e:
                st.warning(f"⚠️ Error reading JSON: {e}")
 
    # -- Upload button (conditional)
    if st.session_state.scraped:
        if st.button("📤 Upload Cleaned JSON to Pinecone"):
            if os.path.exists("scraped_data.json"):
                call_pinecone("scraped_data.json")
            else:
                st.error("❌ File not found. Please scrape again first.")
 
 
if __name__ == "__main__":
    main()