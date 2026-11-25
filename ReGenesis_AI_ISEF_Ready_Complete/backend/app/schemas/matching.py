from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import ConfigDict, BaseModel

class MatchScoreBreakdown(BaseModel):
    category_score: float
    trade_score: float
    quantity_score: float
    purity_score: float
    location_score: float
    price_score: float

class MatchResultResponse(BaseModel):
    id: str
    listing_id: str
    candidate_id: str
    score: float
    explanation: str
    breakdown: Optional[MatchScoreBreakdown] = None
    reasons: List[str] = []
    missing_info: List[str] = []
    suggested_steps: List[str] = []
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Legacy Match Response for compatibility
class LegacyMatchOut(BaseModel):
    score: float
    explanation: str
    id: str
    title: str
    category: str
    trade_type: str
    qty: float
    purity: float
    price: float
    factory: str
    city: str
    bid: str
    btitle: str
    bfactory: str
    bcity: str
    bqty: float
    bprice: float
