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
    # 1. Enterprise Anti-Bot Fortresses & Job Boards
    "glassdoor", "g2", "indeed", "naukri", "yelp", 
    "crunchbase", "zoominfo", "apollo", "trustpilot",
    
    # 2. Hard Login Walls & Social Media
    "facebook", "twitter", "instagram", "youtube", "x.com", "linkedin",
    
    # 3. Aggregators, Directories, and Blogs (The "Not a real company" list)
    "justdial", "indiamart", "ambitionbox", "clutch", "medium",
    "goodfirms", "startupindia", "sulekha", "tradeindia", "indiafilings"
}



def get_base_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "").lower()
    except Exception:
        return url.lower()

# 👇 1. THE ANTI-LISTICLE & ANTI-CRASH FILTER 👇
def is_valid_company_url(domain: str, url: str, title: str) -> bool:
    # Check domain blacklist
    for excluded in EXCLUDED_DOMAINS:
        if excluded in domain:
            return False
            
    url_lower = url.lower()
    title_lower = title.lower()
    
    # 👇 THE CRITICAL FIX: Block files before Playwright clicks them 👇
    # Using endswith() or ? checks avoids accidentally blocking valid URLs like /about-pdf-tools/
    bad_extensions = [".pdf", ".xlsx", ".xls", ".doc", ".docx", ".csv", ".zip", ".png", ".jpg", ".jpeg", ".ppt", ".pptx"]
    if any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in bad_extensions):
        print(f"🛑 Skipping file-link: {url}")
        return False
        
    # Check for obvious blog/listicle patterns in the URL or Title
    spam_patterns = ["top-", "best-", "list-", "top 10", "top 15", "top 20", "directory", "companies-in"]
    if any(spam in url_lower or spam in title_lower for spam in spam_patterns):
        return False
        
    return True

def search_companies_via_serpapi(industry: str, location: str, num_results: int = 30, start_page: int = 0) -> list:
    if not SERPAPI_API_KEY:
        raise ValueError("CRITICAL: SERPAPI_API_KEY is missing from your .env file.")

    # 👇 2. THE NEW GOOGLE DORK 👇 
    # Notice we added -top -best -list -directory to natively block blogs!
    # Change your query string to include these:
    query = f'"{industry}" companies OR business in "{location}" -jobs -top -best -directory -course -academy -event -meetup -community'
    
    
    print(f"🔍 Searching Google for: '{query}'...")

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY, # Ask for extra so we have plenty of backups
        # 👇 ADD THIS: Force Google to give us 50 results!
        "gl": "in",          # (Optional but recommended) Geolocation: India
        "hl": "en",
        "num": 50,  # We can keep this at 10 to process in batches
        "start": start_page 
    }
    
    forbidden_domains = [
        "wikipedia.org", "investopedia.com", "britannica.com", 
        "dictionary.com", "forbes.com", "bloomberg.com", 
        "justdial.com", "indiamart.com", "glassdoor.com",
        "screener.in", "ambitionbox.com", "clutch.co",
        "khanacademy.org", "coursera.org", "udemy.com", 
        "merriam-webster.com", "exportersindia.com", "zixinindia.com", "townscript.com", 
        "zaubacorp.com", "tofler.in", "instafinancials.com", 
        "community.sap.com", "tradeindia.com", "jdmagicbox.com",
        "enrollbusiness.com", "financialcontent.com", 
        "prweb.com", "globenewswire.com", "prnewswire.com",
        "startupindia.gov.in"
    ]

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

            link_lower = link.lower()
            if any(domain in link_lower for domain in forbidden_domains):
                continue

            if ".edu/" in link_lower or link_lower.endswith(".edu"):
                continue

            domain = get_base_domain(link)

            # 👇 3. PASS THE URL AND TITLE TO THE NEW FILTER 👇
            if domain not in seen_domains and is_valid_company_url(domain, link, title):
                seen_domains.add(domain)
                companies.append({
                    "name": title.split("-")[0].split("|")[0].strip(),
                    "url": link,
                    "domain": domain
                })

            if len(companies) >= num_results:
                break

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
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # Give the page a 2-second "breather" to finish any sneaky JavaScript redirects
            await page.wait_for_timeout(2000) 
            
            # Now grab the text
            # This asks: "Does the body exist? If yes, give me the text. If no, give me nothing."
            website_text = await page.evaluate("document.body ? document.body.innerText : ''")
            return website_text
            
        except Exception as e:
            print(f"⚠️ Failed to scrape {url}: {e}")
            return None
        finally:
            await browser.close() # Good practice to explicitly close the browser
        

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