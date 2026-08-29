import os
import json
import random
import uuid
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

supabase: Client = create_client(url, key)

# Kopargaon coordinates roughly
KOP_LAT = 19.8872
KOP_LON = 74.4772

def load_json(filename):
    filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
    with open(filepath, 'r') as f:
        return json.load(f)

def generate_random_coords():
    return (
        KOP_LAT + random.uniform(-0.02, 0.02),
        KOP_LON + random.uniform(-0.02, 0.02)
    )

def seed_data():
    print("Loading Kopargaon JSON datasets...")
    cost_matrix = load_json("kopargaon_water_waste_operational_rules_cost_matrix_v1.json")
    
    print("Clearing existing demo data...")
    # Because of foreign key constraints, clear issues first, then citizens and wards
    supabase.table("issues").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("citizens").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("wards").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("daily_resources").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    print("Seeding Wards and Citizens...")
    wards = []
    for i in range(1, 6):
        res = supabase.table("wards").insert({
            "name": f"Ward {i}",
            "ward_number": i,
            "population": random.randint(5000, 20000),
            "equity_weight": round(random.uniform(0.3, 0.9), 2)
        }).execute()
        wards.append(res.data[0]['id'])
        
    citizens = []
    for i in range(10):
        res = supabase.table("citizens").insert({
            "phone_number": f"9876543{i:03d}",
            "name": f"Citizen {i}"
        }).execute()
        citizens.append(res.data[0]['id'])

    print("Extracting reference costs from JSON...")
    # Extract JCB hourly rate from JSON as a cost basis
    unit_rates = cost_matrix["waste_and_drain_operations"]["drain_desilting_reference_rates"]["unit_rates"]
    jcb_rate = next((r["reference_rate_inr"] for r in unit_rates if r["resource_code"] == "JCB_3DX"), 1400)
    dumper_rate = next((r["reference_rate_inr"] for r in unit_rates if r["resource_code"] == "DUMPER_6W"), 2000)

    print("Seeding Issues (Incidents)...")
    issue_templates = [
        {
            "category": "drain_blockage",
            "desc": "Major drain blockage causing street flooding. Requires JCB.",
            "infra": [0.6, 0.8, 1.0],
            "safety": [0.5, 0.7, 0.9],
            "cost_bounds": [jcb_rate/1000, (jcb_rate+dumper_rate)/1000, (jcb_rate*2+dumper_rate)/1000] # Scaled for TFN
        },
        {
            "category": "water_leakage",
            "desc": "Main distribution pipe leaking near school.",
            "infra": [0.8, 0.9, 1.0],
            "safety": [0.6, 0.8, 1.0],
            "cost_bounds": [0.5, 1.0, 1.5]
        },
        {
            "category": "waste_overflow_near_sensitive_site",
            "desc": "Solid waste overflow near municipal hospital.",
            "infra": [0.4, 0.6, 0.8],
            "safety": [0.7, 0.9, 1.0],
            "cost_bounds": [0.2, 0.5, 0.8]
        },
        {
            "category": "pump_or_electrical_failure",
            "desc": "WTP Pump 2 tripped, reducing water supply to Ward 2.",
            "infra": [0.7, 0.9, 1.0],
            "safety": [0.3, 0.5, 0.7],
            "cost_bounds": [1.0, 2.0, 3.0]
        }
    ]

    issues_to_insert = []
    for i in range(15):
        template = random.choice(issue_templates)
        lat, lon = generate_random_coords()
        ward_id = random.choice(wards)
        
        # We need equity from the ward
        ward_equity = 0.5 # fallback
        
        # Build criteria scores (Fuzzy TFNs)
        # 1. infra_criticality
        # 2. safety_risk
        # 3. equity
        # 4. resource_cost (as cost bounds)
        
        criteria_scores = {
            "infra_criticality": template["infra"],
            "safety_risk": template["safety"],
            "equity": [ward_equity-0.1, ward_equity, ward_equity+0.1],
            "resource_cost": template["cost_bounds"]
        }
        
        issues_to_insert.append({
            "citizen_id": random.choice(citizens),
            "ward_id": ward_id,
            "category": template["category"],
            "description": template["desc"],
            "lat": lat,
            "lon": lon,
            "status": "OPEN",
            "criteria_scores": criteria_scores
        })
        
    supabase.table("issues").insert(issues_to_insert).execute()
    
    print("Seeding Daily Resources Constraint...")
    # Add today's budget (e.g. Rs. 15,000) and workforce limit (e.g. 50 hours)
    supabase.table("daily_resources").insert({
        "record_date": datetime.now().strftime("%Y-%m-%d"),
        "budget_limit": 15000.00,
        "workforce_limit": 50.00
    }).execute()

    print("Seed completed successfully! Database is ready for triage.")

if __name__ == "__main__":
    seed_data()
