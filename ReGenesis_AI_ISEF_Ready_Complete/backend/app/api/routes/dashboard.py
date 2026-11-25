from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.dashboard import (
    DashboardAnalyticsResponse, DemandPredictionReport,
    NegotiationSuggestionRequest, NegotiationSuggestionResponse
)
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.listing_service import ListingService
from backend.app.ai.demand_predictor import DemandPredictor
from backend.app.ai.negotiation_assistant import SmartNegotiationAssistant

router = APIRouter(prefix="/dashboard", tags=["Smart Analytics & Market Intelligence"])

@router.get("/analytics", response_model=DashboardAnalyticsResponse)
def get_dashboard_analytics(db: Session = Depends(get_db)):
    """Fetch live aggregated dashboard KPIs, sector breakdown, and monthly circularity trends."""
    return DashboardService.get_analytics(db)

@router.get("/predictions", response_model=DemandPredictionReport)
def get_demand_predictions(db: Session = Depends(get_db)):
    """Analyze supply & demand velocity to predict future material opportunities & potential shortages."""
    listings = ListingService.list_listings(db, limit=100)
    list_dicts = [ListingService.to_legacy_dict(l) for l in listings]
    return DemandPredictor.predict(list_dicts)

@router.post("/negotiate", response_model=NegotiationSuggestionResponse)
def get_negotiation_guidance(req: NegotiationSuggestionRequest, db: Session = Depends(get_db)):
    """Return comparison guidance from current listings without inventing a fair-market price."""
    listings = ListingService.list_listings(db, limit=500)
    list_dicts = [ListingService.to_legacy_dict(item) for item in listings]
    return SmartNegotiationAssistant.analyze_price(
        material_type=req.material_type,
        quantity=req.quantity,
        purity=req.purity,
        current_asking_price=req.current_asking_price,
        city=req.city,
        market_listings=list_dicts
    )
