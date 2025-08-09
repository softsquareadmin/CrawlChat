#!/bin/bash
# Install Playwright browser before running Streamlit
playwright install chromium
exec streamlit run app.py
