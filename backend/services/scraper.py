import os
import sys
import asyncio
import concurrent.futures
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from playwright.async_api import async_playwright
from dotenv import load_dotenv

from .ai_engine import (
    process_company_batch,
    passes_basic_heuristic
)

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# ── Domain blacklist ──────────────────────────────────────────────────────────
EXCLUDED_DOMAINS = {
    "glassdoor.com", "g2.com", "indeed.com", "naukri.com", "yelp.com",
    "crunchbase.com", "zoominfo.com", "apollo.io", "trustpilot.com",
    "facebook.com", "twitter.com", "instagram.com", "youtube.com", "x.com", "linkedin.com",
    "justdial.com", "indiamart.com", "ambitionbox.com", "clutch.co",
    "medium.com", "goodfirms.co", "sulekha.com", "tradeindia.com", "indiafilings.com", "startupindia.gov.in",
    "imdb.com", "rottentomatoes.com", "wikipedia.org", "fandom.com",
    "vocabulary.com", "dictionary.com", "merriam-webster.com", "theinformation.com", "forbes.com",
    "manufacturing.net", "themanufacturer.com", "manufacturer.com",
    "techcrunch.com", "wired.com", "bloomberg.com", "reuters.com", "wsj.com",
    "sciencedirect.com", "netsuite.com", "investopedia.com", "britannica.com",
    "khanacademy.org", "coursera.org", "udemy.com", "researchgate.net", "springer.com", "springernature.com",
    "tracxn.com", "kompass.com", "zaubacorp.com", "tofler.in",
    "instafinancials.com", "screener.in", "enrollbusiness.com",
    "financialcontent.com", "wellfound.com", "topdevelopers.co",
    "prweb.com", "globenewswire.com", "prnewswire.com",
    "foundit.in", "shine.com", "timesjobs.com", "hirist.com", "instahyre.com",
    "internshala.com", "apna.co", "michaelpage.co.in", "michaelpage.com",
    "randstad.in", "manpower.com", "hays.in", "cutshort.io",
    "f6s.com", "ycombinator.com", "selectedfirms.co",
    "dnb.com", "bajajfinserv.in",
    "geeksforgeeks.org", "w3schools.com", "javatpoint.com", "tutorialspoint.com",
    "guvi.in", "skillogic.com", "pynetlabs.com",
    "magicbricks.com", "99acres.com", "housing.com", "nobroker.in",
    "squareyards.com", "commonfloor.com", "makaan.com", "housiey.com",          
    "advisorkhoj.com", "bankbazaar.com", "policybazaar.com", "etmoney.com",
    "zomato.com", "swiggy.com", "magicpin.com", "tataneu.com", "expedia.co.in", "expedia.com",
    "maps.apple.com", "tripadvisor.com", "tripadvisor.in", "booking.com", "agoda.com", "airbnb.com", "lonelyplanet.com",
    "otestays.com", "incredibleindia.gov.in",
    # State tourism boards — surface for city-name queries
    "gujarattourism.com", "haryanatourism.gov.in", "maharashtratourism.gov.in",
    "rajasthantourism.gov.in", "keralatourism.org", "punjab.gov.in",
    # Startup incubators/accelerators — not companies themselves
    "t-hub.co", "nasscomstartups.in", "startupindia.gov.in",
    "villagetrail.in", "plugandplaytechcenter.com",
    # Dictionary / reference sites that surface for generic industry terms
    "collinsdictionary.com", "oxfordlearnersdictionaries.com",
    "wiktionary.org", "merriam-webster.com",
    # App market intelligence — not a company
    "businessofapps.com", "appfigures.com", "sensortower.com",
    "reddit.com", "quora.com",
    "delhi.gov.in", "delhitourism.gov.in", "india.gov.in",
    "indiaai.gov.in", "mnre.gov.in", "solarrooftop.pmsuryaghar.gov.in",
    "bengaluruurban.nic.in", "peda.gov.in",
    "worldbank.org", "worldometers.info", "nationalgeographic.com", "kids.nationalgeographic.com", "un.org",
    "cnn.com", "edition.cnn.com", "bbc.com", "bbc.co.uk", "ndtvprofit.com", "zeenews.india.com",
    "flipkart.com", "amazon.in", "amazon.com", "snapdeal.com", "solarclue.com", "industrybuying.com",
    "builtinmumbai.in", "builtinpune.in", "builtinsf.com", "builtinchicago.com",
    "syrmasgs.com", "anantgroup.co.in", "scribd.com", "traffictail.com", "barquecontech.com",
    "designrush.com", "zappkode.com", "sutrahr.com",
    "ibm.com", "lenovo.com", "dell.com", "hp.com", "oracle.com",
    "sap.com", "salesforce.com", "servicenow.com", "c3.ai",
    "theknowledgeacademy.com", "muchskills.com", "openedr.com",
    "mygate.com",
    "groww.in", "zerodha.com", "moneycontrol.com", "financial.com",        
    "apps.apple.com", "play.google.com", "public.app", "publictv.in",          
    "solargroup.com",
    "bvp.com", "sequoiacap.com", "accel.com",
    "saasboomi.org", "saasclub.io",
    "freelancer.com", "upwork.com", "fiverr.com", "toptal.com", "computer.com",
    "semiconindia.org", "semi.org", "nasscom.in", "nasscom.com", "ficci.in", "ficci.com",
    "cii.in", "assocham.org", "siam.in", "ieema.org", "phdcci.in", "sia-india.com",
    "india-briefing.com", "tickertape.in", "investindia.gov.in",   
    "ibef.org", "makeinindia.com", "cloud.gov.in",
    "financialexpress.com", "economictimes.indiatimes.com", "livemint.com",
    "business-standard.com", "ndtv.com", "thehindu.com", "hindustantimes.com",
    "ai.google", "search.google", "cloud.google",
    "indianyellowpages.com", "exportersindia.com", "dialme24.com", 
    "jdmagicbox.com", "fundoodata.com", "tofler.in", "zaubacorp.com", 
    "quickcompany.in", "thecompanycheck.com", "grotal.com", 
    "businessdir.in", "dir.indiamart.com"
}

# ── Post-AI aggregator guard ──────────────────────────────────────────────────
_AGGREGATOR_DOMAIN_ROOTS = {
    "internshala", "f6s", "naukri", "glassdoor", "dnb", "clutch",
    "indiamart", "justdial", "ambitionbox", "tradeindia", "kompass",
    "zoominfo", "crunchbase", "tracxn", "wellfound", "screener",
    "builtinpune", "builtinsf", "builtinchicago", "builtinmumbai", "scribd",
    "apna", "geeksforgeeks", "w3schools", "javatpoint", "tutorialspoint",
    "guvi", "skillogic", "pynetlabs", "cutshort", "selectedfirms",
    "designrush", "zappkode", "sutrahr",
    "magicbricks", "99acres", "housing", "nobroker", "squareyards",
    "tataneu", "expedia", "tripadvisor", "otestays", "lonelyplanet",
    "mygate", "reddit", "quora",
    "flipkart", "amazon", "snapdeal", "solarclue", "solargroup",
    "worldbank", "worldometers", "nationalgeographic", "groww",
    "michaelpage", "randstad", "manpower", "ycombinator",
    "financial", "bajajfinserv", "zomato", "swiggy", "magicpin",
    "housiey", "advisorkhoj", "bankbazaar", "policybazaar", "etmoney",
    "bvp", "sequoiacap", "accel", "saasboomi", "saasclub",
    "freelancer", "upwork", "fiverr", "toptal", "computer",
    "semiconindia", "nasscom", "ficci", "cii", "assocham",
    "siam", "ieema", "phdcci", "india-briefing", "tickertape", "investindia",
}

# ── Industry search strategy ──────────────────────────────────────────────────
INDUSTRY_QUERY_STRATEGY: dict[str, tuple[str, list[str]]] = {
    "manufacturing": (
        "{location} precision engineering manufacturer",
        ["auto components manufacturer {location}", "{location} sheet metal fabrication company", "{location} CNC machining company", "industrial equipment manufacturer {location}", "{location} ISO certified manufacturer", "{location} IATF 16949 manufacturer", "plastic injection moulding company {location}", "forging casting company {location}"]
    ),
    "finance": ("{location} financial services company", ["investment firm {location}", "NBFC {location}", "{location} wealth management company"]),
    "it": ("{location} IT services company", ["{location} software solutions firm", "{location} web application development company", "{location} mobile app development company", "{location} SaaS product company", "{location} ERP CRM software company"]),
    "information technology": ("{location} IT services company", ["{location} software solutions firm", "{location} web application development company", "{location} mobile app development company", "{location} SaaS product company"]),
    "cloud": ("{location} cloud services company", ["cloud computing company {location}", "{location} AWS Azure cloud solutions", "{location} managed cloud services"]),
    "ai": ("{location} artificial intelligence company", ["{location} AI ML solutions company", "machine learning company {location}"]),
    "software": ("{location} software development company", ["{location} custom software solutions", "{location} SaaS startup", "{location} web and mobile app company", "{location} software product company"]),
    "logistics": ("{location} logistics company", ["supply chain company {location}", "freight services {location}"]),
    "healthcare": ("{location} healthcare company", ["hospital {location}", "medical services company {location}", "diagnostics company {location}"]),
    "pharma": ("{location} pharmaceutical company", ["pharma company {location}", "drug manufacturer {location}"]),
    "real estate": ("{location} residential property developer",["{location} real estate developer","{location} housing project builder","RERA registered developer {location}","{location} commercial property developer","luxury apartments {location} developer",]),
    "construction": ("{location} construction company", ["civil contractor {location}", "builder {location}"]),
    "automotive": ("{location} automotive company", ["automobile manufacturer {location}", "auto parts company {location}"]),
    "energy": ("{location} energy company", ["solar energy company {location}", "renewable energy {location}"]),
    "insurance": ("{location} insurance company", ["insurance firm {location}", "general insurance {location}"]),
    "banking": ("{location} bank", ["banking services {location}", "NBFC {location}"]),
    "fmcg": ("{location} FMCG company", ["consumer goods company {location}", "packaged goods {location}"]),
    "chemicals": ("{location} chemicals company", ["specialty chemicals {location}", "chemical manufacturer {location}"]),
    "textiles": ("{location} textiles company", ["garment manufacturer {location}", "fabric company {location}"]),
    "cybersecurity": ("{location} cybersecurity company", ["{location} information security firm", "{location} penetration testing company", "{location} SOC managed security services", "{location} cloud security company"]),
    "semiconductor": ("{location} VLSI design company", ["{location} fabless chip design company", "{location} embedded systems company", "{location} semiconductor design center", "ARM RISC-V SoC design {location}", "{location} ASIC design services company", "analog mixed-signal design company {location}", "semiconductor IP company {location}"]),
    "embedded": ("{location} embedded systems company", ["{location} firmware development company", "{location} RTOS embedded software company", "{location} IoT hardware company", "embedded C development company {location}", "{location} microcontroller software company"]),
    "iot": ("{location} IoT solutions company", ["{location} Internet of Things company", "{location} connected devices company", "{location} IoT hardware startup", "industrial IoT company {location}"]),
    "vlsi": ("{location} VLSI design company", ["{location} chip design company", "{location} RTL design services", "{location} physical design company", "EDA VLSI services {location}"]),
    "public relations": ("{location} public relations agency", ["{location} PR communications firm", "{location} corporate communications agency", "{location} media relations company"]),
}

_LOCATION_TYPO_MAP: dict[str, str] = {
    "banagalore": "Bangalore", "bangalroe": "Bangalore", "banglaore": "Bangalore", "bangaolre": "Bangalore",
    "mumabi": "Mumbai", "mumnai": "Mumbai", "mumbai": "Mumbai",
    "dlehi": "Delhi", "dehli": "Delhi",
    "hyderbad": "Hyderabad", "hydrabad": "Hyderabad",
    "chenai": "Chennai",
    "kolkota": "Kolkata", "kolkatta": "Kolkata",
    "ahmedabad": "Ahmedabad", "ahemdabad": "Ahmedabad",
}

_COUNTRY_NAMES = {
    "india", "usa", "united states", "uk", "united kingdom",
    "australia", "canada", "singapore", "germany", "france",
    "japan", "china", "uae", "dubai",
}

def _get_query_templates(raw: str) -> tuple[str, list[str]]:
    key = raw.strip().lower()

    if key in INDUSTRY_QUERY_STRATEGY:
        return INDUSTRY_QUERY_STRATEGY[key]

    for industry_key, strategy in INDUSTRY_QUERY_STRATEGY.items():
        if industry_key in key:
            return strategy

    company_signals = ["company", "services", "firm", "industry", "solutions",
                       "group", "corp", "ltd", "pvt", "manufacturer", "provider"]
    
    if any(s in key for s in company_signals):
        return ("{location} " + raw.strip(), [raw.strip() + " {location}"])

    print(f"⚠️ UNKNOWN INDUSTRY DETECTED: '{raw.strip()}'. Using fallback query.")
    return (
        "{location} " + raw.strip() + " company",
        [raw.strip() + " company {location}"],
    )

def _normalize_to_homepage(url: str) -> str:
    _LOCATOR_SUBDOMAINS = {
        "locate-us", "locate", "stockbroker", "stockbroker-branch",
        "nearme", "near-me", "branch", "branches", "atm",
        "store-locator", "storelocator", "find-us", "findus",
        "offices", "office-locator",
    }
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        bare = netloc.lstrip("www.")
        labels = bare.split(".")
        if len(labels) > 2 and labels[0] in _LOCATOR_SUBDOMAINS:
            bare = ".".join(labels[1:])
            return f"{parsed.scheme}://www.{bare}/"

        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) > 1:
            return f"{parsed.scheme}://{parsed.netloc}/"

        return f"{parsed.scheme}://{parsed.netloc}/{'/'.join(segments)}".rstrip("/") + "/"
    except Exception:
        return url

def get_base_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "").lower()
    except Exception:
        return url.lower()

# ── URL / Title spam filter ───────────────────────────────────────────────────
_URL_PATH_SPAM = [
    "/blog/", "/articles/", "/news/", "/post/", "/posts/", "/resources/", "/learn/", "/guide/", "/tutorial/", "/wiki/",
    "/dictionary/", "/top-", "/best-", "list-of-", "companies-in-", "-companies/", "-companies-", "/explore/", "/company-list",
    "/business-directory", "/glossary", "/definition", "/what-is-", "/types-of-", "/industry/", "/topics/", "/d/legal-entities/",
    "/directory/", "/startups/l/", "/ways-to-search/", "/document/", "-overview", "-pune-central-", "/neighbourhood/",
    "/place?", "/pages/travel/", "/computer-science-fundamentals/", "/think/topics/", "/in/en/glossary/",
    "/companies/type/", "/companies/industry/", "/agency/", "-companies-in-", "/companies/",
    "/jobs/financial-services/", "/jobs-in-", "/jobs/role_", "/building-materials", "/collections/", "/tourism-g", "/destinations/",
    "/geography/countries/", "/world-population/", "/world/india", "/ext/en/country/", "/en/delhi", "/en/karnataka/", "/r/bangalore",
    "/artificial-intelligence-stocks", "/blog/best-artificial-intelligence-stocks", "/en/solar/", "/executive_education/",
    "/som/mba-", "/careers/about-us/locations/", "/branch-locator/", "/locations/it-company-", "/itmanaged/", "ai-companies-in-",
    "/top-ai-startup", "/artificial-intelligence-companies",
]

_TITLE_SPAM = [
    "top 10", "top 15", "top 20", "top 25", "top 50", "top 100", "directory", "magazine", "journal", "gazette", "what is ", "types of ",
    "definition of ", "companies in ", "salaries & benefits", " jobs, salaries", "top companies", "list of companies", "find companies",
    " & salaries", "map, property", "property rates", "overview", "travel guide", "places to visit", "must see places", "must-see places",
    "hotels in ", "it companies in ", "best it companies", "tourist places", "tourism:", "all you need to know", "vacations",
    "and its types", "what is software", "fundamentals of ", "population (20", "country profile", "national portal", "company listing",
    "district ", "government of karnataka", "national portal for rooftop", "ministry of ", "solar energy corporation of india",
    "list of artificial intelligence", " stocks in india", "jobs in kothrud", "jobs in pune", "jobs in bangalore", "jobs in delhi",
    "jobs in mumbai", " jobs ", "recruitment agency in ", "training course in ", "mba banking", "for business managers", "buy solar",
    "solar panels", "industrial machinery", "discover the growth", "find information technology", "staffing services jobs",
    "news, articles and insights", "ai overviews", "national cloud of", "startups in ", "cloud computing companies in", "top cloud computing",
    "dynamic artificial intelligence company in", "ai & machine learning development company in", "ai/ml recruitment agency",
    "ai & machine learning training", "ai & ml solutions", "expert artificial intelligence company in", "it managed service providers in",
    "it company in bangalore",
]

def is_valid_company_url(domain: str, url: str, title: str) -> bool:
    _GOV_TLDS = (".gov.in", ".gov.uk", ".gov.us", ".gov.au", ".nic.in", ".ac.in", ".ac.uk", ".edu.in")
    if any(domain.endswith(tld) for tld in _GOV_TLDS):
        print(f"   🏛️ Gov/Edu TLD filter killed: {url}")
        return False

    for excluded in EXCLUDED_DOMAINS:
        if domain == excluded or domain.endswith("." + excluded):
            return False

    url_lower   = url.lower()
    title_lower = title.lower()

    bad_extensions = [".pdf", ".xlsx", ".xls", ".doc", ".docx", ".csv", ".zip", ".png", ".jpg", ".jpeg", ".ppt", ".pptx"]
    if any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in bad_extensions):
        print(f"🛑 Skipping file-link: {url}")
        return False

    url_path = urlparse(url).path.lower()
    if any(spam in url_path for spam in _URL_PATH_SPAM):
        print(f"   🔍 URL-path filter killed: {url}  (path={url_path})")
        return False

    matched_spam = next((s for s in _TITLE_SPAM if s in title_lower), None)
    if matched_spam:
        print(f"   🔍 Title filter killed: '{title}'  (matched='{matched_spam}')")
        return False

    return True

# ── SerpAPI -site: blocklist ───────────────────────────────────────────────────
_QUERY_BLOCKLIST = " ".join([
    "-site:wikipedia.org", "-site:investopedia.com", "-site:britannica.com", "-site:sciencedirect.com", "-site:netsuite.com",
    "-site:dictionary.com", "-site:vocabulary.com", "-site:forbes.com", "-site:bloomberg.com", "-site:justdial.com", "-site:indiamart.com",
    "-site:glassdoor.com", "-site:screener.in", "-site:ambitionbox.com", "-site:clutch.co", "-site:khanacademy.org", "-site:coursera.org",
    "-site:udemy.com", "-site:merriam-webster.com", "-site:tradeindia.com", "-site:jdmagicbox.com", "-site:zaubacorp.com", "-site:tofler.in",
    "-site:instafinancials.com", "-site:prweb.com", "-site:globenewswire.com", "-site:prnewswire.com", "-site:startupindia.gov.in",
    "-site:researchgate.net", "-site:tracxn.com", "-site:kompass.com", "-site:wellfound.com", "-site:topdevelopers.co", "-site:ibef.org",
    "-site:foundit.in", "-site:shine.com", "-site:financialexpress.com", "-site:economictimes.com", "-site:livemint.com",
    "-site:moneycontrol.com", "-site:business-standard.com", "-site:themanufacturer.com", "-site:manufacturer.com", "-site:cloud.gov.in",
    "-site:ai.google", "-site:search.google", "-site:internshala.com", "-site:f6s.com", "-site:dnb.com", "-site:scribd.com",
    "-site:builtinpune.in", "-site:builtinmumbai.in", "-site:apna.co", "-site:geeksforgeeks.org", "-site:magicbricks.com", "-site:99acres.com",
    "-site:housing.com", "-site:nobroker.in", "-site:squareyards.com", "-site:tataneu.com", "-site:expedia.co.in", "-site:expedia.com",
    "-site:maps.apple.com", "-site:tripadvisor.com", "-site:tripadvisor.in", "-site:mygate.com", "-site:otestays.com", "-site:lonelyplanet.com",
    "-site:traffictail.com", "-site:barquecontech.com", "-site:theknowledgeacademy.com", "-site:muchskills.com", "-site:ibm.com",
    "-site:lenovo.com", "-site:reddit.com", "-site:quora.com", "-site:flipkart.com", "-site:amazon.in", "-site:solarclue.com",
    "-site:worldbank.org", "-site:worldometers.info", "-site:nationalgeographic.com", "-site:kids.nationalgeographic.com", "-site:cnn.com",
    "-site:bbc.com", "-site:bbc.co.uk", "-site:delhi.gov.in", "-site:delhitourism.gov.in", "-site:india.gov.in", "-site:incredibleindia.gov.in",
    "-site:indiaai.gov.in", "-site:bajajfinserv.in", "-site:groww.in", "-site:financial.com", "-site:michaelpage.co.in", "-site:cutshort.io",
    "-site:designrush.com", "-site:zappkode.com", "-site:sutrahr.com", "-site:ycombinator.com", "-site:selectedfirms.co", "-site:c3.ai",
    "-site:solargroup.com", "-site:guvi.in", "-site:skillogic.com", "-site:pynetlabs.com", "-site:apps.apple.com", "-site:bvp.com",
    "-site:saasboomi.org", "-site:freelancer.com", "-site:upwork.com", "-site:fiverr.com", "-site:computer.com", "-site:pmindia.gov.in",
    "-site:theguardian.com", "-site:zomato.com", "-site:swiggy.com", "-site:housiey.com", "-site:advisorkhoj.com", "-site:bankbazaar.com",
    "-site:policybazaar.com", "-site:semiconindia.org", "-site:semi.org", "-site:nasscom.in", "-site:nasscom.com", "-site:ficci.in",
    "-site:ficci.com", "-site:cii.in", "-site:assocham.org", "-site:siam.in", "-site:ieema.org", "-site:phdcci.in", "-site:sia-india.com",
    "-site:india-briefing.com", "-site:tickertape.in", "-site:investindia.gov.in",
])

def _run_serpapi_query(query: str, params: dict) -> list:
    params["q"] = query
    try:
        results = GoogleSearch(params).get_dict()
        return results.get("organic_results", [])
    except Exception as e:
        print(f"❌ SerpAPI query failed: {e}")
        return []

def search_companies_via_serpapi(industry: str, location: str, num_results: int = 30, start_page: int = 0) -> list:
    if not SERPAPI_API_KEY:
        raise ValueError("CRITICAL: SERPAPI_API_KEY is missing from your .env file.")

    location_parts = [p.strip() for p in location.split(",")]
    normalised_parts = []
    for part in location_parts:
        lower = part.lower()
        normalised_parts.append(_LOCATION_TYPO_MAP.get(lower, part))
    location = ", ".join(normalised_parts)
    print(f"📍 Resolved location: '{location}'")

    safe_industry = industry.strip()
    safe_industry = re.sub(r'\bIT\b',     'Information Technology', safe_industry, flags=re.IGNORECASE)
    safe_industry = re.sub(r'\bI\.T\.\b', 'Information Technology', safe_industry, flags=re.IGNORECASE)
    safe_industry = re.sub(r'\bHR\b',     'Human Resources',        safe_industry, flags=re.IGNORECASE)
    safe_industry = re.sub(r'\bPR\b',     'Public Relations',       safe_industry, flags=re.IGNORECASE)

    primary_template, fallback_templates = _get_query_templates(safe_industry)
    primary_query = primary_template.replace("{location}", location)
    fallback_queries = [q.replace("{location}", location) for q in fallback_templates]

    base_params = {
        "engine":  "google",
        "api_key": SERPAPI_API_KEY,
        "gl":      "in",
        "hl":      "en",
        "num":     100,
        "start":   start_page,
    }

    _loc_lower = location.strip().lower()
    _is_country = _loc_lower in _COUNTRY_NAMES
    if _is_country:
        print(f"🌍 Country-level location detected ('{location}'). Queries will use sub-industry specifics.")

    def _make_query(q: str) -> str:
        if _is_country and len(q.split()) <= 3 and "company" not in q.lower():
            q = q + " company"
        return q + " " + _QUERY_BLOCKLIST

    queries_to_try = [_make_query(primary_query)] + [_make_query(q) for q in fallback_queries]

    companies    = []
    seen_domains = set()

    for i, query in enumerate(queries_to_try):
        label = "Primary" if i == 0 else f"Fallback {i}"
        print(f"🔍 [{label}] Searching Google for: '{query[:120]}...'")

        organic_results = _run_serpapi_query(query, dict(base_params))

        if not organic_results:
            print(f"   ↳ 0 raw results. Trying next query...")
            continue

        print(f"   ↳ Got {len(organic_results)} raw results. Filtering...")

        batch_found = 0
        for result in organic_results:
            title = result.get("title", "")
            link  = result.get("link",  "")

            if not link or "google.com" in link:
                continue

            link_lower = link.lower()
            if ".edu/" in link_lower or link_lower.endswith(".edu"):
                continue

            domain = get_base_domain(link)

            if domain not in seen_domains and is_valid_company_url(domain, link, title):
                seen_domains.add(domain)
                homepage_url = _normalize_to_homepage(link)
                companies.append({
                    "name":   title.split("-")[0].split("|")[0].strip(),
                    "url":    homepage_url,
                    "domain": domain,
                })
                batch_found += 1

            if len(companies) >= num_results:
                break

        print(f"   ↳ {batch_found} new companies survived filtering (running total: {len(companies)}).")

        if len(companies) >= num_results:
            break

        if batch_found == 0:
            print(f"   ↳ All results were directories/noise. Trying next query...")

    if not companies:
        print(f"⚠️  All queries returned 0 valid company websites for '{industry}' in '{location}'.")
    else:
        print(f"✅ Found {len(companies)} direct company websites.")

    return companies

# ── Playwright scraping (Windows-safe) ───────────────────────────────────────
async def _playwright_scrape(url: str) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)
            website_text = await page.evaluate(
                "document.body ? document.body.innerText : ''"
            )
            if website_text:
                return " ".join(website_text.split())[:3000]
            return website_text
        except Exception as e:
            print(f"⚠️ Failed to scrape {url}: {e}")
            return None
        finally:
            await browser.close()

def _run_playwright_in_thread(url: str) -> str | None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_playwright_scrape(url))
    finally:
        loop.close()

async def extract_website_text(url: str) -> str | None:
    print(f"🌐 Scraping website: {url}...")
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _run_playwright_in_thread, url)

def _is_aggregator_domain(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.replace("www.", "").lower()
        root = domain.split(".")[0]
        return root in _AGGREGATOR_DOMAIN_ROOTS
    except Exception:
        return False

# ── Batch pipeline ────────────────────────────────────────────────────────────
async def run_batch_pipeline(target_urls_data, sales_inputs, target_location):
    if sales_inputs is None:
        sales_inputs = {}

    approved_companies = []
    current_batch      = []
    BATCH_SIZE         = 10
    
    # We pass the raw string; the local ai_engine bouncer handles synonyms for free.
    keywords_string = sales_inputs.get("Keywords", "")

    for comp in target_urls_data:
        url          = comp["url"]
        website_text = await extract_website_text(url)

        if not passes_basic_heuristic(website_text or "", keywords_string):
            print(f"🚫 Bouncer Rejected: {url}")
            continue

        current_batch.append({
            "url":          url,
            "name":         comp["name"],
            "website_text": website_text,
        })

        if len(current_batch) >= BATCH_SIZE:
            print(f"🚀 Processing Batch of {BATCH_SIZE} companies...")
            batch_results = await process_company_batch(
                current_batch, sales_inputs, target_location
            )
            for result in batch_results:
                source_url = result.get("id", "")
                if _is_aggregator_domain(source_url):
                    print(f"🛡️ Post-AI aggregator guard rejected: {source_url}")
                    continue
                approved_companies.append(result)
            current_batch = []

    if current_batch:
        print(f"🚀 Processing Final Batch of {len(current_batch)} companies...")
        batch_results = await process_company_batch(
            current_batch, sales_inputs, target_location
        )
        for result in batch_results:
            source_url = result.get("id", "")
            if _is_aggregator_domain(source_url):
                print(f"🛡️ Post-AI aggregator guard rejected: {source_url}")
                continue
            approved_companies.append(result)

    return approved_companies