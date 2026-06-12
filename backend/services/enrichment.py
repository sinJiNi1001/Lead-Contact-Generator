"""
===============================================================================
File: services/enrichment.py
Project: Lead Contact Generator
Description: 
    The contact discovery module. Once a company is qualified by the AI Engine, 
    this module attempts to locate the key decision-makers.
    
    Key Responsibilities:
    - Executes targeted search queries to find LinkedIn profiles associated 
      with the specific company domain.
    - Filters search results for C-Suite, VP, and Director-level job titles 
      (e.g., CEO, CTO, Head of Sales).
    - Formats the contact names, designations, and URLs for the CRM database.
===============================================================================
"""
import asyncio
import os
import requests
from dotenv import load_dotenv

from services.ai_engine import extract_linkedin_contact

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY")

# ── Name sanity guard ─────────────────────────────────────────────────────────
# Catches AI hallucinations like "Apna Founder" or "GeeksForGeeks CEO" where the
# "name" field is clearly a company-name + role string, not a real person name.
_COMPANY_NAME_TOKENS = {
    "founder", "ceo", "cto", "coo", "cfo", "vp", "president",
    "director", "manager", "head", "lead", "engineer", "developer",
    "intern", "executive", "officer", "official", "staff", "team",
    "group", "corp", "ltd", "pvt", "inc", "llc", "technologies",
    "solutions", "services", "systems", "ventures", "labs",
}

def _is_real_person_name(name: str) -> bool:
    """
    Returns False if the name looks like 'CompanyName Role' rather than
    a real human first/last name.
    """
    if not name or not name.strip():
        return False
    parts = name.strip().split()
    if len(parts) < 2 or len(parts) > 5:
        return False
    lower_parts = [p.lower().rstrip(".,") for p in parts]
    if any(token in _COMPANY_NAME_TOKENS for token in lower_parts):
        return False
    return True


async def find_linkedin_contacts(
    company_name: str,
    target_roles: list,
    target_location: str,
    keywords: str = "",           # Pass-through so {keywords} in prompt is substituted
) -> list:
    """
    Uses Google X-Ray searching to find actual employees on LinkedIn,
    then uses Groq AI to rigorously verify and extract their exact titles.
    """
    if not SERPAPI_API_KEY:
        print("⚠️ SERPAPI_API_KEY missing in .env. Cannot find contacts.")
        return []

    # ── Build the broad location (city only) for the LinkedIn search dork ────
    # e.g. "Baner, Pune" → "Pune",  "Pune" → "Pune"
    if "," in target_location:
        broad_location = target_location.split(",")[-1].strip()
    else:
        broad_location = target_location

    # ── Build ONE query for all roles — NOT one per role (was causing duplicates) ──
    # The old code had `for role in clean_target_roles[:2]` but never used `role`
    # inside the loop — it always built role_query from the full list, so the
    # same SerpAPI call ran N times and every contact appeared N times in output.
    role_query = " OR ".join([f'"{r.strip().title()}"' for r in target_roles])
    query = f'site:linkedin.com/in "{company_name}" ({role_query}) "{broad_location}"'

    print(f"🔍 Deep Scanning for executives at {company_name} in {target_location}...")

    params = {
        "engine":  "google",
        "q":       query,
        "api_key": SERPAPI_API_KEY,
        "num":     5,
    }

    found_contacts: list = []
    seen_profile_urls: set[str] = set()   # dedup guard against SerpAPI returning same URL twice

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=25)
        data = response.json()

        if "organic_results" not in data:
            return []

        for result in data["organic_results"][:5]:
            profile_url = result.get("link", "")

            # Must be a personal profile, not a company page
            if "linkedin.com/in/" not in profile_url:
                continue

            if profile_url in seen_profile_urls:
                continue
            seen_profile_urls.add(profile_url)

            raw_title = result.get("title", "")
            snippet   = result.get("snippet", "")
            full_text = f"{raw_title}\n{snippet}"

            extracted_data = await extract_linkedin_contact(
                full_text,
                target_roles,
                company_name,
                target_location,
                keywords,         # substitutes {keywords} in pitch_angle prompt
            )
            
            await asyncio.sleep(6)

            # Must return a valid dict with both fields populated
            if not (extracted_data
                    and extracted_data.get("name")
                    and extracted_data.get("designation")):
                print(f"   🚫 AI Rejected Google Result (Title missing or invalid)")
                continue

            if extracted_data.get("is_match") is not True:
                reason = extracted_data.get("reason", "No semantic match.")
                print(f"   🚫 AI Rejected: '{extracted_data.get('name', 'Unknown')}' - {reason}")
                continue

            name        = extracted_data["name"]
            designation = str(extracted_data["designation"])   # guard against bool/None

            # ── Name sanity guard ─────────────────────────────────────────────
            if not _is_real_person_name(name):
                print(f"   🛡️ Name Guardrail Rejected: '{name}' — looks like a company/role string")
                continue

            # ── Garbage title guardrail ───────────────────────────────────────
            bad_words = ["experience", "education", "skills", "location", "past", "previous"]
            target_roles_lower = [r.lower() for r in target_roles]
            if not any("intern" in r or "trainee" in r for r in target_roles_lower):
                bad_words.extend(["intern", "internship", "trainee", "student", "fresher"])

            if any(word in designation.lower() for word in bad_words):
                print(f"   🛡️ Title Guardrail Rejected: '{designation}'")
                continue

            print(f"   🎯 AI Verified & Captured: {name} ({designation})")
            found_contacts.append({
                "name":            name,
                "designation":     designation,
                "linkedin_url":    profile_url,
                "relevance_score": 80,
                "rank":            len(found_contacts) + 1,
                "is_match":        True,
            })

    except Exception as e:
        print(f"⚠️ Error scanning LinkedIn for {company_name}: {e}")

    return found_contacts