# ... your imports ...
import asyncio
import json
import os
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import streamlit as st
import pineconeDataLoad as pineconeDataLoad
import subprocess
import random
from playwright.async_api import async_playwright


@st.cache_resource(show_spinner=False)
def ensure_playwright_browsers():
    # Do NOT use --with-deps on Streamlit Cloud
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
    subprocess.run(["playwright", "install", "chromium"], check=True)
    return True

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
    
    proxy_server = os.getenv("PROXY_SERVER", "http://unblock.oxylabs.io:60000")
    proxy_username = os.getenv("PROXY_USERNAME", "userone_Z0Bw7")
    proxy_password = os.getenv("PROXY_PASSWORD", "Webuserone_1")
 
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": proxy_server,
                "username": proxy_username,
                "password": proxy_password
            },
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--start-maximized",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--ignore-ssl-errors",
                "--ignore-certificate-errors",
                "--ignore-ssl-errors-spki-list",
                "--disable-web-security"
            ]
        )
 
        context = await browser.new_context(
            ignore_https_errors=True,
            bypass_csp=True,
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36",
            java_script_enabled=True,
            accept_downloads=False
        )
 
        # Hide automation flags
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = { runtime: {} };
        """)
 
        page = await context.new_page()
 
        # Always set headers before visiting
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        })
 
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop()
            if url in visited:
                continue
            visited.add(url)
 
            if any(url.startswith(excluded) for excluded in exclude_urls):
                st.write(f"⏭️ Skipping excluded URL: {url}")
                continue
 
            try:
                st.write(f"🔍 Scraping: {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(2)
 
                # Close popups if any
                try:
                    close_popup = await page.query_selector(
                        "button[class*='popup-close'], .close, .close-popup, .login-close"
                    )
                    if close_popup:
                        await close_popup.click()
                        await asyncio.sleep(1)
                        st.write("🔒 Popup closed")
                except:
                    pass
 
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                results[url] = text
 
                # Extract and queue new links
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)
                    parsed = urlparse(full_url)
 
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
