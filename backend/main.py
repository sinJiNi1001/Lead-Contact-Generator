import sys
import asyncio
import uuid

# CRITICAL FIX FOR WINDOWS PLAYWRIGHT + FASTAPI
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# Import our database setup and relational models
from database import SessionLocal, Company, Contact, SearchHistory

# Import our individual engine services
from services.scraper import search_companies_via_serpapi, extract_website_text
from services.ai_engine import analyze_company_with_ai
from services.enrichment import find_linkedin_contacts

app = FastAPI(title="Lead Generation API")

# Add this import at the top
from fastapi.middleware.cors import CORSMiddleware

# Add this block right after defining the app!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # React ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# EPHEMERAL JOB TRACKER (For React Loading Screens)
# ==========================================
# We keep the live status in memory so React can poll it fast,
# while the actual finalized lead data gets saved permanently to PostgreSQL.
JOBS_DB = {}

# ==========================================
# REQUEST BLUEPRINTS (Pydantic)
# ==========================================
class LeadGenerationRequest(BaseModel):
    industry: str
    location: str
    sales_inputs: dict

# ==========================================
# THE BACKGROUND ENGINE (with PostgreSQL)
# ==========================================
async def background_lead_generator(job_id: str, request: LeadGenerationRequest):
    """
    Runs silently in the background: Scrapes -> AI Analyzes -> Enriches -> Saves to DB.
    """
    db = SessionLocal()
    
    try:
        requested_leads = int(request.sales_inputs.get("Number of Leads Required", 3))
        
        JOBS_DB[job_id]["status"] = "scraping_google"
        
        
        # 1. Search Google (Limiting to 3 for testing)
        companies = search_companies_via_serpapi(request.industry, request.location, num_results=requested_leads)
        companies = companies[:requested_leads]
        
        if not companies:
            JOBS_DB[job_id]["status"] = "failed"
            JOBS_DB[job_id]["error"] = "No companies found on Google."
            return

        JOBS_DB[job_id]["status"] = "analyzing_ai"
        
        analyzed_leads = []
        leads_saved_count = 0
        
        # 2. Scrape Websites & Ask AI
        for company in companies:
            print(f"\nProcessing: {company['name']}...")
            text = await extract_website_text(company["url"])
            
            if not text:
                continue
                
            analysis = await analyze_company_with_ai(
                company_name=company["name"],
                company_url=company["url"],
                website_text=text,
                sales_inputs=request.sales_inputs
            )
            
            if analysis:
                JOBS_DB[job_id]["status"] = f"enriching_{company['name']}"
                
                # 3. Enrich Contacts via Google X-Ray
                target_roles = request.sales_inputs.get("Target Roles", ["CTO", "CEO"])
                real_contacts = find_linkedin_contacts(company["name"], target_roles)
                
                if real_contacts:
                    analysis["top_contacts"] = real_contacts
                    
                analyzed_leads.append(analysis)
                
                # ==========================================
                # 4. SAVE TO POSTGRESQL RELATIONAL TABLES
                # ==========================================
                domain = analysis.get("domain", "").lower().strip()
                
                # Check if Company already exists to prevent duplicate rows
                existing_company = db.query(Company).filter(Company.domain == domain).first()
                
                if not existing_company:
                    new_company = Company(
                        name=analysis.get("name"),
                        domain=domain,
                        industry=analysis.get("industry"),
                        location=request.location,
                        lead_score=analysis.get("lead_score"),
                        priority=analysis.get("priority", "Medium"),
                        reason=analysis.get("reason"),
                        signals=analysis.get("signals"),
                        confidence=analysis.get("confidence_score"),
                        source="AI_Pipeline"
                    )
                    db.add(new_company)
                    db.flush() # Generates the new ID without fully committing yet
                    
                    company_db_id = new_company.id
                    leads_saved_count += 1
                else:
                    company_db_id = existing_company.id

                # Save the new Contacts (checking for duplicate LinkedIn URLs)
                if real_contacts:
                    for contact in real_contacts:
                        linkedin_url = contact.get("linkedin_url")
                        
                        if linkedin_url and "unknown" not in linkedin_url.lower():
                            existing_contact = db.query(Contact).filter(Contact.linkedin_url == linkedin_url).first()
                            
                            if not existing_contact:
                                new_contact = Contact(
                                    company_id=company_db_id,
                                    name=contact.get("name"),
                                    designation=contact.get("designation"),
                                    linkedin_url=linkedin_url,
                                    relevance_score=contact.get("relevance_score"),
                                    rank=contact.get("rank")
                                )
                                db.add(new_contact)
                
                # Commit this company and its contacts to the DB safely
                db.commit() 

        # 5. Log the overall Search History
        history_log = SearchHistory(
            user_name="Admin", # Hardcoded until you add user auth later
            input_parameters=request.sales_inputs,
            leads_generated=leads_saved_count
        )
        db.add(history_log)
        db.commit()

        # 6. Update the live React tracker with final JSON
        JOBS_DB[job_id]["status"] = "completed"
        JOBS_DB[job_id]["results"] = analyzed_leads
        print(f"\n✅ Job {job_id} Complete! Saved {leads_saved_count} new companies to PostgreSQL.")

    except Exception as e:
        db.rollback() # If something crashes, undo the database transaction to prevent corruption
        JOBS_DB[job_id]["status"] = "failed"
        JOBS_DB[job_id]["error"] = str(e)
    finally:
        db.close() # Always close the connection back to the database pool

# ==========================================
# THE API ENDPOINTS (React talks to these)
# ==========================================

@app.get("/")
async def root():
    """Health check for the server."""
    return {"message": "Lead Generation API is awake and running!"}

@app.post("/api/generate-leads")
async def start_lead_generation(request: LeadGenerationRequest, background_tasks: BackgroundTasks):
    """
    React calls this first. It creates a job ticket and starts the AI.
    """
    job_id = str(uuid.uuid4())
    
    JOBS_DB[job_id] = {
        "status": "queued",
        "results": [],
        "error": None
    }
    
    background_tasks.add_task(background_lead_generator, job_id, request)
    
    return {"message": "Job started", "job_id": job_id}

@app.get("/api/jobs/{job_id}")
async def check_job_status(job_id: str):
    """
    React calls this every 3 seconds to check loading screen progress.
    """
    if job_id not in JOBS_DB:
        return {"error": "Job not found."}
        
    return JOBS_DB[job_id]

@app.get("/api/jobs")
async def get_all_jobs():
    """
    ADMIN TOOL: View all active jobs in memory.
    """
    return JOBS_DB