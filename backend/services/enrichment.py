import os
import requests
from dotenv import load_dotenv

from services.scraper import SERPAPI_API_KEY


load_dotenv()

# This will catch it regardless of how you named it in your .env file!
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY")

def find_linkedin_contacts(company_name: str, target_roles: list) -> list:
    """
    Uses Google X-Ray searching to find actual employees on LinkedIn
    based on the AI's target roles.
    """
    if not SERPAPI_API_KEY:
        print("⚠️ SERPAPI_API_KEY missing. Cannot find contacts.")
        return []

    found_contacts = []
    
    print(f"🔍 Hunting for executives at {company_name}...")

    # We only look for the top 2 roles to save API credits during testing
    for role in target_roles[:2]:
        # The magical X-Ray query
        query = f'site:linkedin.com/in/ "{role}" "{company_name}"'
        
        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "num": 1 # We only need the top result
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            # Did Google find a LinkedIn profile?
            if "organic_results" in data and len(data["organic_results"]) > 0:
                top_result = data["organic_results"][0]
                
                # Google usually formats the title like "John Doe - CTO - Dreamz Technology | LinkedIn"
                # We split it to try and extract just the name
                raw_title = top_result.get("title", "")
                name = raw_title.split("-")[0].split("|")[0].strip()
                
                profile_url = top_result.get("link", "")
                
                # Make sure it's an actual profile, not a company page or post
                if "linkedin.com/in/" in profile_url:
                    print(f"   🎯 Found: {name} ({role})")
                    found_contacts.append({
                        "name": name,
                        "designation": role,
                        "linkedin_url": profile_url,
                        "relevance_score": 95, # High confidence since Google matched the exact role/company
                        "rank": len(found_contacts) + 1
                    })
                    
        except Exception as e:
            print(f"⚠️ Error finding {role} for {company_name}: {e}")

    return found_contacts