"""
Triage API - Block 1 (Lead Dev)
Handles: Fuzzy TOPSIS scoring, Knapsack allocation, dispatch manifest generation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional
from datetime import datetime, date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import (
    get_db, Ticket, TicketCriteriaScore, DispatchManifest, DispatchManifestItem,
    TicketStatus, DEFAULT_CRITERIA_CONFIG, CRITERIA_TYPES
)

# Import ML engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from track1_engine.prioritization import run_prioritization
from track1_engine.allocation import knapsack_allocate

router = APIRouter(prefix="/api/triage", tags=["triage"])


class TriageRunRequest(BaseModel):
    daily_budget: float
    daily_workforce: float
    ward_id: Optional[str] = None


class TriageRunResponse(BaseModel):
    message: str
    prioritized_count: int
    scheduled_count: int
    deferred_count: int
    manifest_id: str
    total_cci_score: float


class PriorityTicket(BaseModel):
    """Ticket with priority score"""
    id: str
    category: str
    cci_score: float
    cost_estimate: float
    hours_estimate: float
    selected: bool

    class Config:
        from_attributes = True


@router.post("/run", response_model=TriageRunResponse)
def run_triage(request: TriageRunRequest, db: Session = Depends(get_db)):
    """
    Run Fuzzy TOPSIS prioritization and Knapsack allocation on open tickets.

    Process:
    1. Fetch all open/scored tickets
    2. Build fuzzy decision matrix from criteria scores
    3. Run Fuzzy TOPSIS to calculate CCi scores
    4. Apply community multiplier to scores
    5. Run Knapsack optimizer with budget and workforce constraints
    6. Create dispatch manifest and update ticket statuses
    """
    try:
        # Fetch open tickets
        query = db.query(Ticket).filter(Ticket.status.in_(["open", "scored", "deduped"]))
        if request.ward_id:
            query = query.filter(Ticket.ward_id == request.ward_id)

        tickets = query.all()

        if not tickets:
            return TriageRunResponse(
                message="No open tickets to triage.",
                prioritized_count=0,
                scheduled_count=0,
                deferred_count=0,
                manifest_id="",
                total_cci_score=0.0
            )

        # Build tickets_data for TOPSIS
        tickets_data = []
        ticket_objects = []

        for ticket in tickets:
            # Get criteria scores
            scores = db.query(TicketCriteriaScore).filter(
                TicketCriteriaScore.ticket_id == ticket.id
            ).all()

            if not scores:
                # Ticket has no criteria scores, skip
                continue

            # Build decision matrix for this ticket
            score_map = {s.criterion_code: [s.tfn_lower, s.tfn_modal, s.tfn_upper] for s in scores}

            # Ensure all 4 criteria are present
            tfn_scores = []
            for criterion in ['C1_infra', 'C2_safety', 'C3_equity', 'C4_cost']:
                if criterion in score_map:
                    tfn_scores.append(score_map[criterion])
                else:
                    tfn_scores.append([0.5, 0.5, 0.5])  # Default

            # Estimate cost and hours based on category
            cost, hours = _estimate_resources(ticket.category)

            tickets_data.append({
                'id': ticket.id,
                'scores': tfn_scores,
                'budget_cost': cost,
                'workforce_hours': hours
            })
            ticket_objects.append(ticket)

        if not tickets_data:
            return TriageRunResponse(
                message="No tickets with criteria scores found.",
                prioritized_count=0,
                scheduled_count=0,
                deferred_count=0,
                manifest_id="",
                total_cci_score=0.0
            )

        # Run Fuzzy TOPSIS
        criteria_config = {
            'types': ['benefit', 'benefit', 'benefit', 'cost'],
            'weights': DEFAULT_CRITERIA_CONFIG['weights']
        }

        prioritized = run_prioritization(tickets_data, criteria_config)

        # Apply community multiplier and update ticket CCi scores
        for item in prioritized:
            ticket_id = item['id']
            base_cci = item['topsis_score']

            # Find ticket and apply multiplier
            ticket = next((t for t in ticket_objects if t.id == ticket_id), None)
            if ticket:
                adjusted_cci = min(base_cci * ticket.community_multiplier, 1.0)
                ticket.cci_score = adjusted_cci
                ticket.status = TicketStatus.SCORED.value
                db.add(ticket)

            item['cci_score'] = adjusted_cci

        # Sort by adjusted CCI (Topsis already sorted, but re-apply multiplier)
        prioritized.sort(key=lambda x: x['cci_score'], reverse=True)

        # Run Knapsack allocation
        allocated_ids, max_score = knapsack_allocate(
            prioritized,
            request.daily_budget,
            request.daily_workforce
        )

        # Create dispatch manifest
        manifest_id = str(uuid4())
        manifest = DispatchManifest(
            id=manifest_id,
            dispatch_date=date.today(),
            budget_cap=request.daily_budget,
            workforce_cap_hours=request.daily_workforce,
            solver_status="OPTIMAL" if allocated_ids else "INFEASIBLE"
        )
        db.add(manifest)

        # Create manifest items and update ticket statuses
        scheduled_count = 0
        deferred_count = 0

        for item in prioritized:
            ticket_id = item['id']
            selected = ticket_id in allocated_ids

            # Find cost/hours
            ticket_data = next((t for t in tickets_data if t['id'] == ticket_id), None)
            cost = ticket_data['budget_cost'] if ticket_data else 0
            hours = ticket_data['workforce_hours'] if ticket_data else 0

            manifest_item = DispatchManifestItem(
                id=str(uuid4()),
                manifest_id=manifest_id,
                ticket_id=ticket_id,
                selected=1 if selected else 0,
                cost_estimate=cost,
                hours_estimate=hours
            )
            db.add(manifest_item)

            # Update ticket status
            ticket = next((t for t in ticket_objects if t.id == ticket_id), None)
            if ticket:
                if selected:
                    ticket.status = TicketStatus.SCHEDULED.value
                    scheduled_count += 1
                else:
                    ticket.status = TicketStatus.DEFERRED.value
                    deferred_count += 1
                db.add(ticket)

        db.commit()

        return TriageRunResponse(
            message="Triage run successfully.",
            prioritized_count=len(prioritized),
            scheduled_count=scheduled_count,
            deferred_count=deferred_count,
            manifest_id=manifest_id,
            total_cci_score=max_score
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Triage error: {str(e)}")


@router.get("/manifest/{manifest_date}")
def get_manifest(manifest_date: str, db: Session = Depends(get_db)):
    """Get dispatch manifest for a specific date"""
    try:
        query_date = datetime.strptime(manifest_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    manifest = db.query(DispatchManifest).filter(
        DispatchManifest.dispatch_date == query_date
    ).first()

    if not manifest:
        raise HTTPException(status_code=404, detail="No manifest found for this date")

    items = db.query(DispatchManifestItem).filter(
        DispatchManifestItem.manifest_id == manifest.id
    ).all()

    # Get ticket details for selected items
    selected_items = []
    deferred_items = []

    for item in items:
        ticket = db.query(Ticket).filter(Ticket.id == item.ticket_id).first()
        if ticket:
            item_data = {
                "ticket_id": item.ticket_id,
                "selected": bool(item.selected),
                "cost_estimate": item.cost_estimate,
                "hours_estimate": item.hours_estimate,
                "category": ticket.category,
                "cci_score": ticket.cci_score,
                "citizen_phone": ticket.citizen_phone,
                "lat": ticket.lat,
                "lon": ticket.lon,
                "ward_id": ticket.ward_id
            }
            if item.selected:
                selected_items.append(item_data)
            else:
                deferred_items.append(item_data)

    return {
        "manifest_id": manifest.id,
        "dispatch_date": manifest.dispatch_date.isoformat(),
        "budget_cap": manifest.budget_cap,
        "workforce_cap_hours": manifest.workforce_cap_hours,
        "solver_status": manifest.solver_status,
        "summary": {
            "total_tickets": len(items),
            "scheduled": len(selected_items),
            "deferred": len(deferred_items)
        },
        "scheduled": selected_items,
        "deferred": deferred_items
    }


@router.get("/today")
def get_today_manifest(db: Session = Depends(get_db)):
    """Get today's dispatch manifest"""
    today = date.today()
    return get_manifest(today.isoformat(), db)


@router.get("/priorities")
def get_priority_list(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get tickets sorted by priority (CCi score)"""
    query = db.query(Ticket).filter(Ticket.cci_score.isnot(None))

    if status:
        query = query.filter(Ticket.status == status)

    tickets = query.order_by(Ticket.cci_score.desc()).limit(limit).all()

    return {
        "tickets": [
            {
                "id": t.id,
                "citizen_phone": t.citizen_phone,
                "category": t.category,
                "cci_score": t.cci_score,
                "status": t.status,
                "community_multiplier": t.community_multiplier,
                "ward_id": t.ward_id,
                "lat": t.lat,
                "lon": t.lon
            }
            for t in tickets
        ],
        "total": len(tickets)
    }


def _estimate_resources(category: str) -> tuple:
    """
    Estimate budget cost and workforce hours based on category.
    These are rough estimates in INR and hours.
    """
    estimates = {
        'pothole': (5000, 8),          # ₹5,000, 8 hours
        'waterlogging': (15000, 16),    # ₹15,000, 16 hours
        'sanitation': (8000, 10),       # ₹8,000, 10 hours
        'water_quality': (25000, 24),   # ₹25,000, 24 hours
        'streetlight': (3000, 4),       # ₹3,000, 4 hours
        'garbage': (4000, 6),           # ₹4,000, 6 hours
        'infrastructure': (50000, 40),    # ₹50,000, 40 hours
        'other': (5000, 6)              # ₹5,000, 6 hours
    }
    return estimates.get(category.lower(), estimates['other'])
