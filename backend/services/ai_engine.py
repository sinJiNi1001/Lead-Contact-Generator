import os
import json
import time
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()
groq_client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

# 👇 GLOBAL SESSION TOKEN TRACKER 👇
SESSION_TOKENS_USED = 0

# ── 1. HELPER: load prompt files ─────────────────────────────────────────────

def load_prompt(filename: str) -> str:
    """Loads a text prompt from the backend/prompts directory."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# ── 2. ZERO-COST BOUNCER (with semantic synonym expansion) ───────────────────

_INDUSTRY_SYNONYMS: dict[str, list[str]] = {
    "semiconductor":    ["vlsi", "chip", "soc", "asic", "fpga", "embedded", "microcontroller", "microprocessor", "rtl", "fabless", "integrated circuit", "analog", "mixed-signal", "arm", "risc-v", "eda", "physical design", "verification", "wafer", "foundry", "fab", "ic design"],
    "embedded":         ["firmware", "rtos", "microcontroller", "microprocessor", "iot", "bare metal", "device driver", "bsp", "bootloader", "arm cortex", "stm32", "esp32", "yocto", "linux kernel", "real-time", "hardware abstraction"],
    "vlsi":             ["chip design", "rtl", "asic", "fpga", "soc", "synthesis", "place and route", "timing", "functional verification", "dv", "eda", "cadence", "synopsys"],
    "iot":              ["internet of things", "connected devices", "smart sensor", "mqtt", "edge computing", "firmware", "lora", "zigbee", "industrial iot", "iiot", "m2m", "telemetry", "connected"],
    "ai":               ["artificial intelligence", "machine learning", "deep learning", "neural network", "nlp", "computer vision", "generative", "llm", "predictive", "automation", "intelligent"],
    "cybersecurity":    ["security", "penetration", "soc", "siem", "firewall", "compliance", "vulnerability", "threat", "infosec", "zero trust", "endpoint", "cloud security"],
    "public relations": ["pr agency", "communications", "media relations", "brand communications", "reputation", "press", "publicity", "corporate communications", "pr firm"],
    "manufacturing":    ["manufactur", "fabricat", "assembl", "production", "plant", "factory", "machining", "industrial", "precision", "forging", "casting", "stamping", "welding", "tooling", "cnc"],
    "finance":          ["financial", "banking", "investment", "lending", "capital", "wealth", "insurance", "fintech", "asset management", "brokerage", "equity", "fund", "portfolio", "trading"],
    "information technology": ["software", "technology", "digital", "solutions", "systems", "tech", "cloud", "data", "saas", "erp", "crm", "devops", "infrastructure", "it services"],
    "it":               ["software", "technology", "digital", "solutions", "systems", "tech", "cloud", "data", "it services"],
    "logistics":        ["supply chain", "freight", "shipping", "warehouse", "transport", "distribution", "courier", "cargo", "fleet"],
    "healthcare":       ["hospital", "clinic", "medical", "pharma", "health", "diagnostic", "patient", "therapeutics", "biotech"],
    "real estate":      ["property", "realty", "housing", "commercial", "residential", "leasing", "developer", "infrastructure"],
    "retail":           ["store", "ecommerce", "e-commerce", "shop", "consumer", "merchandise", "d2c", "direct to consumer"],
    "education":        ["school", "college", "university", "learning", "training", "edtech", "curriculum", "institution", "academy"],
    "construction":     ["contractor", "builder", "civil", "structural", "infrastructure", "erection", "project management"],
    "automotive":       ["automobile", "vehicle", "car", "truck", "fleet", "oem", "spare parts", "ev", "electric vehicle"],
    "agriculture":      ["agri", "farming", "crop", "irrigation", "fertilizer", "agribusiness", "harvest"],
    "energy":           ["power", "solar", "wind", "renewable", "oil", "gas", "utilities", "electricity", "generation"],
    "insurance":        ["insurer", "underwriting", "reinsurance", "claims", "policy", "actuarial"],
    "banking":          ["bank", "nbfc", "credit", "deposit", "loan", "mortgage", "microfinance"],
    "telecom":          ["telecommunications", "network", "broadband", "wireless", "spectrum", "connectivity"],
    "chemicals":        ["chemical", "polymer", "resin", "compound", "specialty", "petrochemical", "agrochemical", "adhesive"],
    "textiles":         ["textile", "fabric", "garment", "apparel", "yarn", "weaving", "knitting", "dyeing", "fashion"],
    "fmcg":             ["consumer goods", "packaged goods", "brand", "distribution", "fmcg company", "personal care", "food"],
}

def _get_synonyms_for_keyword(keyword: str) -> list[str]:
    kw = keyword.lower().strip()
    
    if kw in _INDUSTRY_SYNONYMS:
        return _INDUSTRY_SYNONYMS[kw]
        
    for industry_key, synonyms in _INDUSTRY_SYNONYMS.items():
        if industry_key in kw or kw in industry_key:
            return synonyms
            
    for industry_key, synonyms in _INDUSTRY_SYNONYMS.items():
        if any(kw == syn or kw in syn or syn in kw for syn in synonyms):
            return synonyms
            
    return []

def passes_basic_heuristic(website_text: str, keywords_string: str) -> bool:
    if not website_text or not website_text.strip():
        return True # Let AI handle blank pages
    if not keywords_string:
        return True

    text = website_text.lower()
    keywords = [k.strip().lower() for k in keywords_string.split(",") if k.strip()]

    for keyword in keywords:
        if keyword in text:
            return True
            
        synonyms = _get_synonyms_for_keyword(keyword)
        if any(syn in text for syn in synonyms):
            return True
            
    return False

# ── 3. BATCH PROCESSOR ───────────────────────────────────────────────────────

async def process_company_batch(company_batch: list, sales_inputs: dict, target_location: str):
    if not company_batch:
        return []

    batch_payload = [
        {
            "id":   comp["url"],
            "name": comp["name"],
            "text": comp["website_text"][:4000], # Strict token diet
        }
        for comp in company_batch
    ]
    payload_string = json.dumps(batch_payload)

    raw_prompt    = load_prompt("company_analyzer.txt")
    keywords_str  = sales_inputs.get("Keywords", "")

    system_prompt = (
        raw_prompt
        .replace("[SALES_INPUTS]",    json.dumps(sales_inputs))
        .replace("[TARGET_LOCATION]", target_location)
        .replace("{keywords}",        keywords_str)
        + "\n\nCRITICAL BATCH INSTRUCTION: You will receive a JSON array of companies. "
          "You MUST evaluate every single company in the array. "
          "Return a JSON object with a single key 'results' containing an array of your evaluations. "
          'The output MUST look like: {"results": [ {"id": "url1", "name": "...", ...}, {"id": "url2", ...} ]}'
    )

    for attempt in range(3):
        try:
            raw_response = await groq_client.chat.completions.with_raw_response.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system",  "content": system_prompt},
                    {"role": "user",    "content": f"Analyze this batch: {payload_string}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            response = await raw_response.parse()

            # Session telemetry
            global SESSION_TOKENS_USED
            used = response.usage.total_tokens if response.usage else 0
            SESSION_TOKENS_USED += used
            daily_left = 500_000 - SESSION_TOKENS_USED
            print(f"📊 [BATCH AI] Burned: {used} | Session Total: {SESSION_TOKENS_USED} | Daily Budget Left: {daily_left}/500000")

            content = response.choices[0].message.content or '{"results": []}'
            return json.loads(content).get("results", [])

        except Exception as e:
            if "429" in str(e):
                await asyncio.sleep(5 * (attempt + 1))
            else:
                print(f"⚠️ Groq Batch Analysis Failed: {e}")
                return []
                
    return []

# ── 4. SINGLE COMPANY ANALYZER (Legacy) ───────────────────────────────────────

async def analyze_company_with_ai(company_name, company_url, website_text, sales_inputs, target_location):
    if not passes_basic_heuristic(website_text, sales_inputs.get("Keywords", "")):
        print(f"🚫 Zero-Cost Bouncer Rejected: {company_url}")
        return {
            "name":             company_name,
            "lead_score":       0,
            "priority":         "Low",
            "reason":           "Failed basic keyword/synonym check. Cost: 0 tokens.",
            "signals":          [],
            "confidence_score": 1.0,
        }

    try:
        clean_text   = website_text[:8000]
        keywords_str = sales_inputs.get("Keywords", "")

        raw_prompt    = load_prompt("company_analyzer.txt")
        system_prompt = (
            raw_prompt
            .replace("[SALES_INPUTS]",    json.dumps(sales_inputs, indent=2))
            .replace("[COMPANY_URL]",     company_url)
            .replace("[WEBSITE_TEXT]",    clean_text)
            .replace("[TARGET_LOCATION]", target_location)
            .replace("{keywords}",        keywords_str) 
        )

        for attempt in range(3):
            try:
                response = await groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": f"Analyze: {company_name}"},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                
                content = response.choices[0].message.content
                if not content:
                    print(f"⚠️ Groq returned no content for {company_name}")
                    return None
                return json.loads(content)

            except Exception as e:
                if "429" in str(e):
                    wait_time = 5 * (attempt + 1)
                    print(f"⚠️ Rate limit for {company_name}. Attempt {attempt + 1}/3. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"⚠️ Groq Analysis Failed for {company_name}: {e}")
                    return None

    except Exception as e:
        print(f"⚠️ Fatal Error in Company AI Engine: {e}")
        return None

# ── 5. LINKEDIN EXTRACTOR ────────────────────────────────────────────────────

async def extract_linkedin_contact(linkedin_snippet_text: str, target_roles: list, company_name: str, target_location: str, keywords: str = "") -> dict:
    try:
        raw_prompt = load_prompt("linkedin_extractor.txt")

        system_prompt = (
            raw_prompt
            .replace("[TARGET_ROLES]",       json.dumps(target_roles))
            .replace("[LINKEDIN_SNIPPET]",   linkedin_snippet_text)
            .replace("[COMPANY_NAME]",       company_name)
            .replace("[TARGET_LOCATION]",    target_location)
            .replace("{keywords}",           keywords)
        )

        raw_response = await groq_client.chat.completions.with_raw_response.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        response = await raw_response.parse()

        # Session telemetry
        global SESSION_TOKENS_USED
        used = response.usage.total_tokens if response.usage else 0
        SESSION_TOKENS_USED += used
        daily_left = 500_000 - SESSION_TOKENS_USED
        print(f"📊 [LINKEDIN AI] Burned: {used} | Session Total: {SESSION_TOKENS_USED} | Daily Budget Left: {daily_left}/500000")

        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    except Exception as e:
        print(f"⚠️ LinkedIn Extraction Failed: {e}")
        return {"is_match": False}