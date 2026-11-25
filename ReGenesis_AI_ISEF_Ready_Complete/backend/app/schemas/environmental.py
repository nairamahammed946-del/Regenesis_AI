from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import ConfigDict, BaseModel, Field

class CarbonCalculationRequest(BaseModel):
    material_type: str = "خشب"
    tonnage: float = Field(gt=0)
    emission_factor: Optional[float] = Field(default=None, gt=0)

class CarbonCalculationResponse(BaseModel):
    material_type: str
    tonnage: float
    co2_factor: float
    co2_avoided_tons: float
    trees_equivalent: Optional[int] = None
    esg_grade: str
    calculation_basis: str
    disclaimer: str

class ProfitCalculationRequest(BaseModel):
    material_type: str
    quantity_tons: float = Field(gt=0)
    waste_selling_price_per_ton: float = Field(ge=0)
    virgin_material_price_per_ton: float = Field(ge=0)
    processing_cost_per_ton: float = Field(default=15.0)
    transport_distance_km: float = Field(default=25.0)
    transport_rate_per_ton_km: float = Field(default=0.15)

class ProfitCalculationResponse(BaseModel):
    material_type: str
    quantity_tons: float
    potential_selling_revenue: float
    buyer_raw_material_savings: float
    total_processing_cost: float
    total_transport_cost: float
    net_economic_benefit: float
    roi_estimated_months: Optional[float] = None
    assumptions_summary: List[str]
    disclaimer: str

class SustainabilityScoreResponse(BaseModel):
    factory_id: str
    factory_name: str
    overall_score: float
    waste_reuse_score: float
    material_exchange_score: float
    waste_diversion_score: float
    environmental_impact_score: float
    resource_efficiency_score: float
    badge_level: str
    evaluation_formula_explained: str
    last_evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ESGCertificateRequest(BaseModel):
    factory_id: Optional[str] = None
    factory_name: Optional[str] = None
    material_type: str
    tonnage: float
    emission_factor: Optional[float] = Field(default=None, gt=0)
