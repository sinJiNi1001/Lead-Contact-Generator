import os
import json
import asyncio
import urllib.request
import urllib.error
from dotenv import load_dotenv
from pydantic import ValidationError

try:
    from schemas import CompanyAnalysisSchema
except ModuleNotFoundError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from schemas import CompanyAnalysisSchema

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

def _sync_ollama_request(prompt: str) -> dict | None:
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json", 
        "stream": False
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    with urllib.request.urlopen(req, timeout=600.0) as response:
        return json.loads(response.read().decode('utf-8'))

async def analyze_company_with_ai(company_name: str, company_url: str, website_text: str, sales_inputs: dict) -> dict | None:
    if not website_text or len(website_text) < 50:
        return {"error": "Not enough website text to analyze."}

    print(f"🧠 Sending {company_name} to local {OLLAMA_MODEL} for analysis...")

    prompt = f"""
    You are an expert B2B Sales Intelligence AI. 
    Analyze the company data against the Sales Target Criteria.

    ### Sales Target Criteria:
    {json.dumps(sales_inputs, indent=2)}

    ### Company Data:
    Name: {company_name}
    URL: {company_url}
    Website Text: {website_text[:1000]}

    ### Instructions:
    1. Calculate a lead_score from 0 to 100.
    2. Write a 1-sentence reason for your score.
    3. Extract positive buying signals as an object (key-value pairs).
    4. Estimate your confidence_score as a decimal between 0.0 and 1.0.
    5. List top_contacts. Use "Unknown" for names and a dummy URL for LinkedIn.
    
    CRITICAL DATA CLEANLINESS RULES:
    1. "name": Extract ONLY the bare company name. Strip out all marketing fluff, SEO taglines, locations, or legal entities (LLC, Pvt Ltd).
   - BAD: "Mplussoft | Custom Software Development Company in Pune"
   - GOOD: "Mplussoft"
   - BAD: "Acme Corp Ltd."
   - GOOD: "Acme Corp"

     2. "domain": Extract ONLY the root domain from the provided URL. Do NOT include 'https://', 'www.', or any trailing paths.
   - BAD: "https://www.ajackus.com/software-development-company-in-pune/"
   - GOOD: "ajackus.com"
   
    3.DIRECTORY FILTER: If the website text describes a list, a directory, or a ranking of other companies (e.g., 'Top 20 companies', 'TechBehemoths directory'), 
    set the lead_score to 0 and set priority to 'N/A'. I only want the service providers themselves."

    You MUST return ONLY a raw JSON object that strictly matches this exact structure. Do not include markdown, code blocks, or extra text.
    
    EXPECTED JSON FORMAT:
    {{
      "name": "{company_name}",
      "domain": "{company_url.replace('https://', '').replace('http://', '').replace('www.', '')}",
      "industry": "{sales_inputs.get('Industry', 'Unknown')}",
      "lead_score": 85,
      "reason": "They are a good fit because they build enterprise software in Pune.",
      "signals": {{"expansion": "expanding team", "audience": "enterprise clients"}},
      "confidence_score": 0.9,
      "top_contacts": {json.dumps([{"name": "Unknown", "designation": r, "linkedin_url": "https://linkedin.com/in/unknown", "relevance_score": 80, "rank": 1} for r in sales_inputs.get('Target Roles', ['CTO'])])}
    }}
    """

    try:
        response_data = await asyncio.to_thread(_sync_ollama_request, prompt)
        if not response_data:
            return None
        ai_output = response_data.get("response", "{}")
        validated_data = CompanyAnalysisSchema.model_validate_json(ai_output)
        
        print(f"✅ AI Analysis Complete! Score: {validated_data.lead_score}/100")
        return validated_data.model_dump(mode='json')

    except urllib.error.URLError as e:
        print(f"❌ Failed to connect to Ollama via urllib: {e}")
        return None
    except ValidationError as e:
        print(f"❌ AI returned improperly formatted JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return None