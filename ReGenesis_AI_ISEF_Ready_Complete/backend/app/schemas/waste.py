from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import ConfigDict, BaseModel, Field

class WasteCategoryResponse(BaseModel):
    id: int
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    co2_factor: float
    icon: Optional[str] = "fa-recycle"

    model_config = ConfigDict(from_attributes=True)

class WasteListingBase(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    category: str
    trade_type: str = "عرض (توفر مخلفات)"
    quantity: float = Field(gt=0)
    unit: str = "طن"
    purity: float = Field(ge=0, le=100, default=90.0)
    price: float = Field(ge=0, default=0.0)
    currency: str = "EGP"
    city: str
    description: Optional[str] = ""
    images: Optional[List[str]] = []
    video_path: Optional[str] = None

class WasteListingCreate(WasteListingBase):
    factory_name: Optional[str] = None
    factory_id: Optional[str] = None

class WasteListingUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    trade_type: Optional[str] = None
    quantity: Optional[float] = None
    purity: Optional[float] = None
    price: Optional[float] = None
    city: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class WasteListingResponse(WasteListingBase):
    id: str
    legacy_code: Optional[str] = None
    factory_id: Optional[str] = None
    factory_name: str
    status: str
    lab_verified: bool
    ai_match_hint: Optional[str] = None
    data_origin: str = "user_submitted"
    price_basis: str = "seller_entered"
    images_are_illustrative: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Legacy Schema for 100% backward compatibility with original frontend
class LegacyListingIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    category: str
    tradeType: str
    qty: float = Field(gt=0)
    purity: float = Field(ge=0, le=100)
    price: float = Field(ge=0)
    factory: str
    city: str
    desc: Optional[str] = ""
    images: Optional[List[str]] = []

class LegacyListingOut(BaseModel):
    id: str
    title: str
    category: str
    tradeType: str
    qty: float
    purity: float
    price: float
    factory: str
    city: str
    desc: str
    aiMatch: str

# 12-factor Material Analysis Schema
class MaterialAnalysisResult(BaseModel):
    id: Optional[str] = None
    predicted_category: str
    predicted_material_type: str
    visual_characteristics: List[str]
    color: str
    shape: str
    approximate_size: str
    visible_contamination: str
    material_condition: str
    potential_applications: List[str]
    possible_recycling_methods: List[str]
    suggested_reuse_opportunities: List[str]
    confidence_score: float
    testing_recommendations: List[str]
    analysis_mode: str = "AI_RuleBased_VisionEngine"
    lab_verification_status: str = "Pending Laboratory Validation"
    disclaimer: str = (
        "This visual report is an AI/Rule-based prediction and does not substitute for certified chemical laboratory testing."
    )
    image_paths: Optional[List[str]] = []
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
