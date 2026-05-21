import os
import json
import time
from groq import AsyncGroq
from dotenv import load_dotenv

# Load API keys
load_dotenv()
groq_client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

# 1. HELPER FUNCTION TO LOAD PROMPTS
def load_prompt(filename: str) -> str:
    """Loads a text prompt from the backend/prompts directory."""
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', filename)
    with open(prompt_path, 'r', encoding='utf-8') as file:
        return file.read()

# 2. COMPANY ANALYZER (WITH RATE-LIMIT RETRY)
async def analyze_company_with_ai(company_name, company_url, website_text, sales_inputs, target_location):
    try:
        clean_text = website_text[:8000] 
        
        # Load the raw text and inject variables
        raw_prompt = load_prompt('company_analyzer.txt')
        system_prompt = raw_prompt.replace("[SALES_INPUTS]", json.dumps(sales_inputs, indent=2)) \
                                  .replace("[COMPANY_URL]", company_url) \
                                  .replace("[WEBSITE_TEXT]", clean_text) \
                                  .replace("[TARGET_LOCATION]", target_location)
        
        # --- 🛡️ RATE LIMIT RETRY LOOP (3 ATTEMPTS) ---
        for attempt in range(3):
            try:
                response = await groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze: {company_name}"}
                    ],
                    response_format={"type": "json_object"}, 
                    temperature=0.1
                )
                content = response.choices[0].message.content
                if not content:
                    print(f"⚠️ Groq Analysis returned no content for {company_name}")
                    return None
                return json.loads(content)
                
            except Exception as e:
                # Catch rate limits specifically
                if "429" in str(e):
                    wait_time = 5 * (attempt + 1)
                    print(f"⚠️ Rate limit hit for {company_name}. Attempt {attempt+1}/3. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"⚠️ Groq Analysis Failed for {company_name}: {e}")
                    return None
                    
    except Exception as e:
        print(f"⚠️ Fatal Error in Company AI Engine: {e}")
        return None

# 3. LINKEDIN EXTRACTOR 
async def extract_linkedin_contact(linkedin_snippet_text, target_roles, company_name, target_location):
    try:
        raw_prompt = load_prompt('linkedin_extractor.txt')
        
        # Inject validation variables
        system_prompt = raw_prompt.replace("[TARGET_ROLES]", json.dumps(target_roles)) \
                                  .replace("[LINKEDIN_SNIPPET]", linkedin_snippet_text) \
                                  .replace("[COMPANY_NAME]", company_name) \
                                  .replace("[TARGET_LOCATION]", target_location)

        # We keep this simple; the enrichment.py logic handles filtering logic
        response = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"⚠️ LinkedIn Extraction Failed: {e}")
        return {"is_match": False}