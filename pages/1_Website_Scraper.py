import streamlit as st
import asyncio
import os
import json
from scrape_module import scrape_to_json
import pineconeDataLoad as pineconeDataLoad

st.set_page_config(page_title="Website Scraper", layout="wide")

st.title("🕷️ Website Scraper & Viewer")
st.write("Enter a base URL to scrape and extract all reachable text content.")

url = st.text_input("🔗 Website URL", placeholder="https://www.example.com")

use_custom_limit = st.checkbox("Customize Max Pages to Scrape", value=False)
if use_custom_limit:
    max_pages = st.slider("🔢 Max Pages", 1, 500, 50)
else:
    max_pages = 50
    st.caption("ℹ️ Default: 50 pages")

output_path = "scraped_data.json"

if os.path.exists(output_path):
    os.remove(output_path)

if st.button("🚀 Start Scraping"):
    if not url.strip():
        st.warning("Please enter a valid URL.")
    else:
        if os.path.exists(output_path):
            os.remove(output_path)

        with st.spinner("Scraping..."):
            asyncio.run(scrape_to_json(url.strip(), output_path, max_pages))
        st.success("✅ Done scraping!")
        with st.spinner("Your data is now being loaded into the vector store. Please wait.."):
            pineconeDataLoad.uploadFileOnPonecone(output_path)
        st.success("✅ Done Uploading!")
        

        st.download_button("⬇️ Download Scraped Data", open(output_path, "rb"), file_name="scraped_data.json")

# Show preview
if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if data:
            st.subheader("📄 Preview")
            preview = dict(list(data.items())[:3])
            st.json(preview)
