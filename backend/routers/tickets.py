"""
Ticket Ingestion API - Block 1 (Lead Dev)
Handles: citizen submission, image deduplication, ticket creation
"""
import os
import uuid
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from PIL import Image

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, Ticket, TicketMedia, TicketCategory, TicketStatus, TicketCriteriaScore
from utils.deduplication import generate_phash, is_duplicate

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# Ensure upload directory exists
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class TicketResponse(BaseModel):
    """Response model for ticket creation"""
    id: str
    citizen_phone: str
    category: str
    description: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    ward_id: Optional[str]
    status: str
    community_multiplier: float
    is_duplicate: bool
    parent_ticket_id: Optional[str]
    message: str

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    """Response for listing tickets"""
    tickets: List[dict]
    total: int


class CriteriaScoreInput(BaseModel):
    """Input for fuzzy criteria scores"""
    infra_lower: float = Field(0.5, ge=0, le=1)
    infra_modal: float = Field(0.7, ge=0, le=1)
    infra_upper: float = Field(0.9, ge=0, le=1)
    safety_lower: float = Field(0.6, ge=0, le=1)
    safety_modal: float = Field(0.8, ge=0, le=1)
    safety_upper: float = Field(1.0, ge=0, le=1)
    equity_lower: float = Field(0.2, ge=0, le=1)
    equity_modal: float = Field(0.5, ge=0, le=1)
    equity_upper: float = Field(0.8, ge=0, le=1)
    cost_lower: float = Field(0.3, ge=0, le=1)
    cost_modal: float = Field(0.5, ge=0, le=1)
    cost_upper: float = Field(0.7, ge=0, le=1)


@router.post("/submit", response_model=TicketResponse)
async def submit_ticket(
    citizen_phone: str = Form(..., description="Citizen WhatsApp phone number"),
    category: str = Form(..., description="Issue category"),
    description: Optional[str] = Form(None, description="Issue description"),
    lat: Optional[float] = Form(None, description="GPS latitude"),
    lon: Optional[float] = Form(None, description="GPS longitude"),
    ward_id: Optional[str] = Form(None, description="Ward identifier"),
    file: UploadFile = File(..., description="Photo of the issue"),
    db: Session = Depends(get_db)
):
    """
    Submit a new grievance ticket with photo.

    Process:
    1. Validate and save image
    2. Generate perceptual hash for deduplication
    3. Check for duplicates within geo-radius
    4. If duplicate: attach to parent, increment community multiplier
    5. If new: create ticket with OPEN status
    6. Assign default fuzzy criteria scores based on category
    """
    try:
        # Validate category
        if category not in [c.value for c in TicketCategory]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Valid options: {[c.value for c in TicketCategory]}"
            )

        # Read image bytes
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Generate perceptual hash
        try:
            phash = generate_phash(image_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image processing error: {str(e)}")

        # Check for duplicates - get all existing hashes from DB
        existing_hashes = []
        if lat is not None and lon is not None:
            # Get near tickets (simplified: within same ward or all open tickets)
            from sqlalchemy import text
            result = db.execute(text("""
                SELECT t.id, m.phash FROM tickets t
                JOIN ticket_media m ON m.ticket_id = t.id
                WHERE t.status IN ('open', 'scored', 'deduped')
                AND t.lat IS NOT NULL AND t.lon IS NOT NULL
            """))
            for row in result:
                existing_hashes.append((row[0], row[1]))

        # Check for duplicate using Hamming distance
        parent_ticket_id = None
        is_dup = False
        for ticket_id, stored_hash in existing_hashes:
            if stored_hash and is_duplicate(phash, [stored_hash], threshold=10):
                parent_ticket_id = ticket_id
                is_dup = True
                break

        if is_dup and parent_ticket_id:
            # Update parent ticket's community multiplier
            parent = db.query(Ticket).filter(Ticket.id == parent_ticket_id).first()
            if parent:
                parent.community_multiplier = min(parent.community_multiplier + 0.15, 3.0)
                parent.updated_at = datetime.utcnow()

            # Create new ticket as duplicate
            ticket_id = str(uuid.uuid4())
            ticket = Ticket(
                id=ticket_id,
                citizen_phone=citizen_phone,
                category=category,
                description=description,
                lat=lat,
                lon=lon,
                ward_id=ward_id,
                status=TicketStatus.DEDUPED.value,
                community_multiplier=1.0,
                is_duplicate=1,
                parent_ticket_id=parent_ticket_id
            )
            db.add(ticket)

            # Save media with hash
            file_path = UPLOAD_DIR / f"{ticket_id}_{file.filename}"
            with open(file_path, "wb") as f:
                await file.seek(0)
                f.write(await file.read())

            media = TicketMedia(
                id=str(uuid.uuid4()),
                ticket_id=ticket_id,
                file_path=str(file_path),
                phash=str(phash)
            )
            db.add(media)
            db.commit()

            return TicketResponse(
                id=ticket_id,
                citizen_phone=citizen_phone,
                category=category,
                description=description,
                lat=lat,
                lon=lon,
                ward_id=ward_id,
                status=TicketStatus.DEDUPED.value,
                community_multiplier=1.0,
                is_duplicate=True,
                parent_ticket_id=parent_ticket_id,
                message="Issue logged as duplicate. Similar report already exists; community severity increased."
            )

        # Create new ticket
        ticket_id = str(uuid.uuid4())
        ticket = Ticket(
            id=ticket_id,
            citizen_phone=citizen_phone,
            category=category,
            description=description,
            lat=lat,
            lon=lon,
            ward_id=ward_id,
            status=TicketStatus.OPEN.value,
            community_multiplier=1.0,
            is_duplicate=0,
            parent_ticket_id=None
        )
        db.add(ticket)

        # Save media with hash
        file_path = UPLOAD_DIR / f"{ticket_id}_{file.filename}"
        with open(file_path, "wb") as f:
            await file.seek(0)
            f.write(await file.read())

        media = TicketMedia(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            file_path=str(file_path),
            phash=str(phash)
        )
        db.add(media)

        # Assign default criteria scores based on category
        # These are hardcoded defaults; real system uses fuzzy AHP from experts
        category_scores = _get_default_scores_for_category(category)

        for criterion_code, (lower, modal, upper) in category_scores.items():
            score = TicketCriteriaScore(
                id=str(uuid.uuid4()),
                ticket_id=ticket_id,
                criterion_code=criterion_code,
                tfn_lower=lower,
                tfn_modal=modal,
                tfn_upper=upper
            )
            db.add(score)

        db.commit()

        return TicketResponse(
            id=ticket_id,
            citizen_phone=citizen_phone,
            category=category,
            description=description,
            lat=lat,
            lon=lon,
            ward_id=ward_id,
            status=TicketStatus.OPEN.value,
            community_multiplier=1.0,
            is_duplicate=False,
            parent_ticket_id=None,
            message="Issue logged successfully."
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


def _get_default_scores_for_category(category: str) -> dict:
    """
    Get default fuzzy criteria scores based on category.
    Lower/Modal/Upper = TFN triple for each criterion.
    """
    # Default medium scores
    default = {
        'C1_infra': [0.5, 0.7, 0.9],
        'C2_safety': [0.5, 0.7, 0.9],
        'C3_equity': [0.3, 0.5, 0.7],
        'C4_cost': [0.4, 0.6, 0.8]
    }

    # Category-specific adjustments
    category_defaults = {
        'pothole': {
            'C1_infra': [0.6, 0.8, 1.0],  # Infrastructure critical
            'C2_safety': [0.7, 0.85, 1.0],  # Safety risk
            'C3_equity': [0.3, 0.5, 0.7],
            'C4_cost': [0.2, 0.4, 0.6]   # Low cost
        },
        'waterlogging': {
            'C1_infra': [0.7, 0.9, 1.0],  # Critical flooding
            'C2_safety': [0.8, 0.95, 1.0],  # High safety risk
            'C3_equity': [0.4, 0.6, 0.8],
            'C4_cost': [0.5, 0.7, 0.9]   # Variable cost
        },
        'sanitation': {
            'C1_infra': [0.4, 0.6, 0.8],
            'C2_safety': [0.5, 0.7, 0.9],  # Health risk
            'C3_equity': [0.5, 0.7, 0.9],  # Equity concern
            'C4_cost': [0.3, 0.5, 0.7]
        },
        'water_quality': {
            'C1_infra': [0.8, 0.9, 1.0],  # Critical infrastructure
            'C2_safety': [0.9, 0.95, 1.0],  # Public health emergency
            'C3_equity': [0.7, 0.85, 1.0],  # Universal impact
            'C4_cost': [0.5, 0.7, 0.9]
        },
        'infrastructure': {
            'C1_infra': [0.8, 0.95, 1.0],  # Critical
            'C2_safety': [0.6, 0.8, 1.0],
            'C3_equity': [0.4, 0.6, 0.8],
            'C4_cost': [0.6, 0.8, 1.0]   # High cost
        },
    }

    return category_defaults.get(category, default)


@router.get("/list", response_model=TicketListResponse)
def list_tickets(
    status: Optional[str] = None,
    ward_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List tickets with optional filters"""
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)
    if ward_id:
        query = query.filter(Ticket.ward_id == ward_id)

    tickets = query.order_by(Ticket.created_at.desc()).limit(limit).all()
    total = query.count()

    return TicketListResponse(
        tickets=[{
            "id": t.id,
            "citizen_phone": t.citizen_phone,
            "category": t.category,
            "status": t.status,
            "cci_score": t.cci_score,
            "community_multiplier": t.community_multiplier,
            "is_duplicate": bool(t.is_duplicate),
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "lat": t.lat,
            "lon": t.lon
        } for t in tickets],
        total=total
    )


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Get ticket details with criteria scores"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get criteria scores
    scores = db.query(TicketCriteriaScore).filter(
        TicketCriteriaScore.ticket_id == ticket_id
    ).all()

    return {
        "id": ticket.id,
        "citizen_phone": ticket.citizen_phone,
        "category": ticket.category,
        "description": ticket.description,
        "lat": ticket.lat,
        "lon": ticket.lon,
        "ward_id": ticket.ward_id,
        "status": ticket.status,
        "cci_score": ticket.cci_score,
        "community_multiplier": ticket.community_multiplier,
        "is_duplicate": bool(ticket.is_duplicate),
        "parent_ticket_id": ticket.parent_ticket_id,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "criteria_scores": [{
            "criterion": s.criterion_code,
            "tfn": [s.tfn_lower, s.tfn_modal, s.tfn_upper]
        } for s in scores]
    }
