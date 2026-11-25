from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class DashboardKPIs(BaseModel):
    total_waste_registered_tons: float
    total_active_listings: int
    active_factories_count: int
    successful_matches_count: int
    pending_purchase_requests: int
    completed_orders_count: int
    estimated_waste_reused_tons: float
    estimated_co2_avoided_tons: float
    estimated_economic_savings_usd: float

class CategoryChartItem(BaseModel):
    category: str
    tonnage: float
    percentage: float
    color: str

class TrendChartItem(BaseModel):
    month: str
    matches: int
    co2_reduced_tons: float
    traded_tons: float

class DashboardAnalyticsResponse(BaseModel):
    kpis: DashboardKPIs
    category_distribution: List[CategoryChartItem]
    monthly_trends: List[TrendChartItem]

# Advisor Schemas
class AdvisorIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list, max_length=12)

class AdvisorOut(BaseModel):
    answer: str
    records_considered: int
    mode: str  # database-grounded-rules / llm-enhanced
    suggested_actions: Optional[List[str]] = []
    sources: Optional[List[Dict[str, str]]] = []

# Demand Prediction Schema
class DemandPredictionItem(BaseModel):
    material_category: str
    trend: str  # Surging Demand, High Supply, Stable, Potential Shortage
    confidence_level: str
    active_demand_tons: float
    active_supply_tons: float
    price_outlook: str
    recommendation: str

class DemandPredictionReport(BaseModel):
    status: str
    historical_data_sufficiency: str
    predictions: List[DemandPredictionItem]
    notes: str

# Smart Negotiation Schema
class NegotiationSuggestionRequest(BaseModel):
    material_type: str
    quantity: float
    purity: float
    current_asking_price: float
    city: str

class NegotiationSuggestionResponse(BaseModel):
    material_type: str
    category_matched: str
    quantity_tons: float
    purity_entered_percent: float
    current_asking_price: float
    currency: str = "EGP"
    comparables_count: int
    submitted_listing_price_min: Optional[float] = None
    submitted_listing_price_max: Optional[float] = None
    recommended_min_price: Optional[float] = None
    recommended_max_price: Optional[float] = None
    fair_market_price: Optional[float] = None
    historical_platform_average: Optional[float] = None
    data_status: str
    basis_of_estimate: List[str]
    negotiation_tips: List[str]
    disclaimer: str
