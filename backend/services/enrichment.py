import os
import requests
from dotenv import load_dotenv

# Import the Groq-powered AI function we built in ai_engine.py
from services.ai_engine import extract_linkedin_contact

load_dotenv()

# Safely grab the SerpAPI key regardless of how it's named in .env
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY")

async def find_linkedin_contacts(company_name: str, target_roles: list, target_location: str) -> list:
    """
    Uses Google X-Ray searching to find actual employees on LinkedIn,
    then uses Groq AI to rigorously verify and extract their exact titles.
    """
    if not SERPAPI_API_KEY:
        print("⚠️ SERPAPI_API_KEY missing in .env. Cannot find contacts.")
        return []
    
    clean_target_roles = [role.strip().title() for role in target_roles]

    found_contacts = []
    
    print(f"🔍 Deep Scanning for executives at {company_name} in {target_location}...")

    # We only look for the top 2 roles to save API credits
    for role in clean_target_roles[:2]:
        # Change how you build the role query
        role_query = " OR ".join([f'"{r}"' for r in target_roles]) 
        
        if "," in target_location:
            broad_location = target_location.split(",")[-1].strip()
        else:
            broad_location = target_location

        # Update the final dork to look like this:
        query = f'site:linkedin.com/in "{company_name}" ({role_query}) "{broad_location}"'
        
        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "api_key": SERPAPI_API_KEY,
            # 👇 VACUUM MODE: Ask for 5 results instead of 1! 👇
            "num": 5 
        }

        try:
            response = requests.get(url, params=params, timeout=25)
            data = response.json()
            
            # 👇 VACUUM MODE: Loop through ALL 5 results instead of just the first one 👇
            if "organic_results" in data:
                for result in data["organic_results"][:5]:
                    profile_url = result.get("link", "")
                    
                    # Make sure it's an actual profile, not a company page
                    if "linkedin.com/in/" in profile_url:
                        
                        # Combine the title and snippet to give Groq maximum context
                        raw_title = result.get("title", "")
                        snippet = result.get("snippet", "")
                        full_text_to_analyze = f"{raw_title}\n{snippet}"
                        
                        # Pass the text to Groq for strict extraction
                        extracted_data = await extract_linkedin_contact(full_text_to_analyze, target_roles, company_name, target_location)
                        
                        # Validate that Groq actually returned a valid JSON dict
                        if extracted_data and extracted_data.get('name') and extracted_data.get('designation'):
                            
                            # 👇 SEMANTIC BOUNCER CHECK 👇
                            if extracted_data.get('is_match') is True:
                                
                                # 🛡️ DYNAMIC GARBAGE TITLE GUARDRAIL 🛡️
                                bad_words = ["experience", "education", "skills", "location", "past", "previous"]
                                
                                # Only block 'intern' or 'trainee' if the user didn't specifically ask for them
                                target_roles_lower = [r.lower() for r in target_roles]
                                if not any("intern" in r or "trainee" in r for r in target_roles_lower):
                                    bad_words.extend(["intern", "internship", "trainee", "student", "fresher"])

                                designation_lower = extracted_data.get('designation', '').lower()
                                
                                if any(word in designation_lower for word in bad_words):
                                    print(f"   🛡️ Python Guardrail Rejected Title: '{extracted_data.get('designation')}'")
                                    continue # Skip this lead immediately
                                
                                print(f"   🎯 AI Verified & Captured: {extracted_data['name']} ({extracted_data['designation']})")
                                
                                found_contacts.append({
                                    "name": extracted_data['name'],
                                    "designation": extracted_data['designation'],
                                    "linkedin_url": profile_url,
                                    "relevance_score": 80, 
                                    "rank": len(found_contacts) + 1,
                                    "is_match": True
                                })
                                # Notice there is NO 'break' statement here! 
                                # It will keep looping to find more matches!
                            else:
                                # 👇 PRINT THE AI'S EXPLANATION 👇
                                reason = extracted_data.get('reason', 'No semantic match.')
                                print(f"   🚫 AI Rejected: '{extracted_data.get('name', 'Unknown')}' - {reason}")
                        else:
                            print(f"   🚫 AI Rejected Google Result (Title missing or invalid)")
                        
        except Exception as e:
            print(f"⚠️ Error finding {role} for {company_name}: {e}")

    return found_contacts