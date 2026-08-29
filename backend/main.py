"""
Kopargaon Civic Resource Prioritization Platform (CRPP)
Main FastAPI Application - 8-Hour MVP
"""
import sys
import os

# Add the parent directory to sys.path so we can import track1_engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uuid

# Import routers
from routers.tickets import router as tickets_router
from routers.triage import router as triage_router
from routers.webhooks import router as webhooks_router

# Initialize database
from database import init_db

# Create FastAPI app
app = FastAPI(
    title="Kopargaon CRPP API",
    description="Civic Resource Prioritization Platform MVP",
    version="0.1.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tickets_router)
app.include_router(triage_router)
app.include_router(webhooks_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized successfully")


@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "Kopargaon Civic Resource Prioritization Platform (CRPP) MVP",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "tickets": "/api/tickets",
            "triage": "/api/triage",
            "webhooks": "/webhooks"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "kopargaon-crpp"}
