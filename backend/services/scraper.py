# services/scraper.py
import os
import sys
import asyncio
import concurrent.futures
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


EXCLUDED_DOMAINS = {
    # 1. Enterprise Anti-Bot Fortresses
    "glassdoor", "g2", "indeed", "naukri", "yelp", 
    "crunchbase", "zoominfo", "apollo", "trustpilot",
    
    # 2. Hard Login Walls (Removed LinkedIn from here)
    "facebook", "twitter", "instagram", "youtube"
}

def get_base_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "").lower()
    except Exception:
        return url.lower()

def is_valid_company_domain(domain: str) -> bool:
    for excluded in EXCLUDED_DOMAINS:
        if excluded in domain:
            return False
    return True

def search_companies_via_serpapi(industry: str, location: str, num_results: int = 15) -> list:
    if not SERPAPI_API_KEY:
        raise ValueError("CRITICAL: SERPAPI_API_KEY is missing from your .env file.")

    query = f'"{industry}" company in {location} -jobs -glassdoor'
    print(f"🔍 Searching Google for: '{query}'...")

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": num_results,
        "gl": "in",
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        organic_results = results.get("organic_results", [])

        companies = []
        seen_domains = set()

        for result in organic_results:
            title = result.get("title", "")
            link = result.get("link", "")

            if not link or "google.com" in link:
                continue

            domain = get_base_domain(link)

            if domain not in seen_domains and is_valid_company_domain(domain):
                seen_domains.add(domain)
                companies.append({
                    "name": title.split("-")[0].split("|")[0].strip(),
                    "url": link,
                    "domain": domain
                })

        print(f"✅ Found {len(companies)} direct company websites.")
        return companies

    except Exception as e:
        print(f"❌ SerpAPI Search Failed: {e}")
        return []

# ---- Playwright scraping (Windows-safe) ----

async def _playwright_scrape(url: str) -> str | None:
    """Actual Playwright logic — always called inside its own clean event loop."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # Tell Playwright to wait until the basic HTML is fully loaded
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Give the page a 2-second "breather" to finish any sneaky JavaScript redirects
            await page.wait_for_timeout(2000) 
            
            # Now grab the text
            # This asks: "Does the body exist? If yes, give me the text. If no, give me nothing."
            website_text = await page.evaluate("document.body ? document.body.innerText : ''")
            return website_text
            
        except Exception as e:
            print(f"⚠️ Failed to scrape {url}: {e}")
            return None
        

def _run_playwright_in_thread(url: str) -> str | None:
    """Runs Playwright in a dedicated thread with its own clean event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_playwright_scrape(url))
    finally:
        loop.close()

async def extract_website_text(url: str) -> str | None:
    """Offloads Playwright to a thread pool so it never conflicts with FastAPI's loop."""
    print(f"🌐 Scraping website: {url}...")
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _run_playwright_in_thread, url)