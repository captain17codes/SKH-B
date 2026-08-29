from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class IssueCreate(BaseModel):
    citizen_phone: str = Field(..., description="Phone number of the citizen reporting the issue")
    category: str = Field(..., description="Category of the issue, e.g., pothole, drainage")
    description: Optional[str] = Field(None, description="Detailed description of the grievance")
    lat: Optional[float] = Field(None, description="Latitude of the issue")
    lon: Optional[float] = Field(None, description="Longitude of the issue")
    ward_id: Optional[str] = Field(None, description="UUID of the ward")

class IssueResponse(BaseModel):
    id: str
    category: str
    description: Optional[str]
    status: str
    topsis_score: Optional[float]
    community_multiplier: int
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    message: Optional[str] = None

class ResourceUpdate(BaseModel):
    budget_used: float
    workforce_used: float
