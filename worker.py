import os
import asyncio
from celery import Celery
import base64

# Ensure event loop for async functions
def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

# Celery App Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "aethel_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# We need to import the heavy functions from main.py
# However, importing main.py directly might cause circular imports or load FastAPI unnecessarily.
# Since this is a refactor, we will import what we need from main.py and structure_agent, evaluator_agent, etc.

@celery_app.task(bind=True)
def process_resume_task(self, pdf_b64, filename, ext, role, jd_skills, user_id):
    # Update state
    self.update_state(state='PROGRESS', meta={'status': 'Extracting text...'})
    
    # We will import here to avoid circular imports if worker is imported by main
    from main import (
        extract_resume_text, _strip_pii, structure_resume, _generate_skills_for_role,
        evaluate_resume, _pool, record_bias_deltas, create_scan_record
    )
    import asyncio
    
    loop = get_or_create_eventloop()
    
    pdf_bytes = base64.b64decode(pdf_b64)
    resume_text = extract_resume_text(pdf_bytes, ext)
    
    self.update_state(state='PROGRESS', meta={'status': 'Stripping PII (Bot 1)...'})
    
    # We run the async tasks synchronously in the Celery worker thread
    pii_result = loop.run_until_complete(loop.run_in_executor(_pool, _strip_pii, resume_text))
    sanitized = pii_result["sanitized_text"]
    
    self.update_state(state='PROGRESS', meta={'status': 'Structuring Resume (Bot 3)...'})
    
    if jd_skills.strip():
        jd_skills_list = [s.strip() for s in jd_skills.split(",") if s.strip()]
        structured_data = loop.run_until_complete(loop.run_in_executor(_pool, structure_resume, sanitized))
    else:
        skills_future = loop.run_in_executor(_pool, _generate_skills_for_role, role)
        struct_future = loop.run_in_executor(_pool, structure_resume, sanitized)
        jd_skills_list, structured_data = loop.run_until_complete(asyncio.gather(skills_future, struct_future))
        
    # ... Wait, moving the ENTIRE analyze_resume logic from main.py to worker.py is risky because it contains 
    # a lot of inline logic (like the fallback groq prompt, database interaction, etc).
    # Is there a cleaner way?
