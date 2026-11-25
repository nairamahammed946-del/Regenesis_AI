from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.matching import MatchResultResponse, LegacyMatchOut
from backend.app.services.matching_service import MatchingService
from backend.app.ai.matching_engine import SmartMatchingEngine

router = APIRouter(prefix="/matching", tags=["AI Smart Matching Engine"])

@router.get("", response_model=List[LegacyMatchOut])
def get_active_matches(limit: int = 30, db: Session = Depends(get_db)):
    """Fetch active AI-scored matches between supply and demand listings."""
    return MatchingService.get_legacy_matches(db, limit)

@router.post("/evaluate")
def evaluate_pair(supply_listing: Dict[str, Any], demand_listing: Dict[str, Any]):
    """Evaluate compatibility score and breakdown for two arbitrary material specifications."""
    score, details = SmartMatchingEngine.score_listings(supply_listing, demand_listing)
    return details
