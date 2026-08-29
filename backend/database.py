"""
Database configuration and models for Kopargaon CRPP MVP
Block 1 - Backend Lead Dev
"""
import os
from datetime import datetime
from typing import Optional, List
from uuid import uuid4, UUID
import enum

from sqlalchemy import create_engine, Column, String, Float, DateTime, Enum, ForeignKey, Text, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.types import TypeDecorator

# Use SQLite for MVP (fastest setup), switch to PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kopargaon_crpp.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    DEDUPED = "deduped"
    SCORED = "scored"
    SCHEDULED = "scheduled"
    DISPATCHED = "dispatched"
    DEFERRED = "deferred"
    RESOLVED = "resolved"


class TicketCategory(str, enum.Enum):
    POTHOLE = "pothole"
    WATERLOGGING = "waterlogging"
    SANITATION = "sanitation"
    WATER_QUALITY = "water_quality"
    STREETLIGHT = "streetlight"
    GARBAGE = "garbage"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class Ticket(Base):
    """Main grievance ticket entity - MVP simplified schema"""
    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_phone = Column(String(15), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    description = Column(Text)
    lat = Column(Float)
    lon = Column(Float)
    ward_id = Column(String(10))

    status = Column(String(20), default=TicketStatus.OPEN.value, index=True)
    community_multiplier = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Scoring fields
    cci_score = Column(Float)  # Closeness Coefficient from TOPSIS
    is_duplicate = Column(Integer, default=0)  # 0=False, 1=True
    parent_ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=True)

    # Relationships
    media = relationship("TicketMedia", back_populates="ticket", cascade="all, delete-orphan")
    scores = relationship("TicketCriteriaScore", back_populates="ticket", cascade="all, delete-orphan")


class TicketMedia(Base):
    """Media attachments (photos) with pHash for deduplication"""
    __tablename__ = "ticket_media"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    file_path = Column(String(500), nullable=False)  # Local path or S3 key
    phash = Column(String(64), nullable=False, index=True)  # Perceptual hash (hex)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="media")


class TicketCriteriaScore(Base):
    """Fuzzy criteria scores (TFN: lower, modal, upper) for TOPSIS"""
    __tablename__ = "ticket_criteria_scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    criterion_code = Column(String(20), nullable=False)  # C1_infra, C2_safety, C3_equity, C4_cost

    tfn_lower = Column(Float, nullable=False)
    tfn_modal = Column(Float, nullable=False)
    tfn_upper = Column(Float, nullable=False)

    ticket = relationship("Ticket", back_populates="scores")


class DispatchManifest(Base):
    """Daily dispatch manifest from Knapsack optimizer"""
    __tablename__ = "dispatch_manifests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dispatch_date = Column(DateTime, nullable=False, index=True)
    budget_cap = Column(Float, nullable=False)
    workforce_cap_hours = Column(Float, nullable=False)
    solver_status = Column(String(20))  # OPTIMAL, FEASIBLE, INFEASIBLE
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("DispatchManifestItem", back_populates="manifest", cascade="all, delete-orphan")


class DispatchManifestItem(Base):
    """Individual tickets in a dispatch manifest"""
    __tablename__ = "dispatch_manifest_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    manifest_id = Column(String(36), ForeignKey("dispatch_manifests.id"), nullable=False)
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    selected = Column(Integer, default=0)  # 0=False, 1=True
    cost_estimate = Column(Float)
    hours_estimate = Column(Float)

    manifest = relationship("DispatchManifest", back_populates="items")


class NotificationLog(Base):
    """WhatsApp notification delivery log"""
    __tablename__ = "notification_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    citizen_phone = Column(String(15), nullable=False)
    template_name = Column(String(50))
    status = Column(String(20), default="queued")  # queued, sent, delivered, failed
    wa_message_id = Column(String(100))
    error_message = Column(Text)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database initialization
def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# MVP Criteria weights (hardcoded for 8-hour sprint)
# In production, these come from Fuzzy AHP expert calibration
DEFAULT_CRITERIA_CONFIG = {
    'types': ['benefit', 'benefit', 'benefit', 'cost'],
    'weights': [
        [0.6, 0.8, 1.0],   # C1_infra: Infrastructural Criticality
        [0.8, 0.9, 1.0],   # C2_safety: Public Safety & Health Risk
        [0.3, 0.5, 0.7],   # C3_equity: Socio-Spatial Equity
        [0.4, 0.6, 0.8]    # C4_cost: Resource Requirement
    ],
    'names': ['C1_infra', 'C2_safety', 'C3_equity', 'C4_cost']
}


# Criteria type mapping (benefit = higher is better, cost = lower is better)
CRITERIA_TYPES = {
    'C1_infra': 'benefit',
    'C2_safety': 'benefit',
    'C3_equity': 'benefit',
    'C4_cost': 'cost'
}
