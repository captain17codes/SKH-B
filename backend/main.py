import sys
import os
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uuid

# Add the parent directory to sys.path so we can import track1_engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import IssueResponse, ResourceUpdate
from backend.utils.deduplication import generate_phash, is_duplicate
from track1_engine.prioritization import run_prioritization
from track1_engine.allocation import knapsack_allocate

app = FastAPI(title="Civic Resource Prioritization API")

# Add CORS Middleware to allow your friend's frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock database of existing hashes to simulate the database deduplication check
mock_db_hashes = []

# Mock data for criteria config (Fuzzy TOPSIS weights)
MOCK_CRITERIA_CONFIG = {
    'types': ['benefit', 'benefit', 'benefit', 'cost'],
    'weights': [
        [0.6, 0.8, 1.0], # infra_criticality
        [0.8, 0.9, 1.0], # safety_risk
        [0.3, 0.5, 0.7], # equity
        [0.4, 0.6, 0.8]  # resource_cost
    ]
}

@app.post("/api/issues", response_model=IssueResponse)
async def submit_issue(
    citizen_phone: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    ward_id: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    # Read the image file and generate perceptual hash
    image_bytes = await file.read()
    phash = generate_phash(image_bytes)
    
    # Check for duplicates using the Hamming distance threshold of 10
    is_dup, duplicate_of = is_duplicate(phash, mock_db_hashes, threshold=10)
    
    # Stub: Normally, here we would insert this record into the Supabase 'issues' table.
    # If is_dup is True, we set duplicate_of_issue_id and increment community_multiplier.
    # We'll mock the response.
    
    if not is_dup:
        mock_db_hashes.append(phash)
        
    issue_id = str(uuid.uuid4())
    
    return IssueResponse(
        id=issue_id,
        category=category,
        description=description,
        status="OPEN",
        topsis_score=None,
        community_multiplier=2 if is_dup else 1,
        is_duplicate=is_dup,
        duplicate_of_id=duplicate_of,
        message="Issue logged successfully."
    )

@app.post("/api/triage/run")
async def run_triage(daily_budget: float, daily_workforce: float):
    """
    Runs the Fuzzy TOPSIS prioritization and the Knapsack allocation on open issues.
    Normally, it fetches OPEN issues from the database.
    We stub this with dummy open issues to demonstrate integration.
    """
    # Stub: Mock open issues fetched from DB
    mock_open_issues = [
        {'id': 't1', 'budget_cost': 500, 'workforce_hours': 10, 'scores': [[0.7, 0.8, 0.9], [0.8, 0.9, 1.0], [0.1, 0.2, 0.3], [0.7, 0.8, 0.9]]}, 
        {'id': 't2', 'budget_cost': 200, 'workforce_hours': 5,  'scores': [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.1, 0.2, 0.3]]},
        {'id': 't3', 'budget_cost': 300, 'workforce_hours': 4,  'scores': [[0.3, 0.4, 0.5], [0.4, 0.5, 0.6], [0.8, 0.9, 1.0], [0.2, 0.3, 0.4]]} 
    ]
    
    # 1. Prioritize open issues
    prioritized_issues = run_prioritization(mock_open_issues, MOCK_CRITERIA_CONFIG)
    
    # 2. Allocate based on constrained daily resources
    allocated_ids, max_score = knapsack_allocate(prioritized_issues, daily_budget, daily_workforce)
    
    # Stub: Normally, update the DB to set status="SCHEDULED" for allocated_ids 
    # and "DEFERRED" for the rest, and update daily_resources table.
    
    return {
        "message": "Triage run successfully.",
        "prioritized_list": prioritized_issues,
        "scheduled_for_today": allocated_ids,
        "max_achieved_topsis_sum": max_score
    }
