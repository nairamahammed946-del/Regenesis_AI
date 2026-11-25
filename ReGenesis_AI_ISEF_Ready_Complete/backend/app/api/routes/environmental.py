import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.environmental import (
    CarbonCalculationRequest, CarbonCalculationResponse,
    ProfitCalculationRequest, ProfitCalculationResponse,
    ESGCertificateRequest
)
from backend.app.services.environmental_service import EnvironmentalService

router = APIRouter(prefix="/environmental", tags=["Carbon Footprint & Sustainability"])

@router.post("/carbon-calculator", response_model=CarbonCalculationResponse)
def calculate_carbon(req: CarbonCalculationRequest):
    """Estimate CO2 emissions avoided and planted tree equivalence with transparent factors."""
    try:
        return EnvironmentalService.calculate_carbon(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.post("/profit-calculator", response_model=ProfitCalculationResponse)
def calculate_profit(req: ProfitCalculationRequest):
    """Calculate economic value, purchasing savings, and ROI from circular waste transactions."""
    return EnvironmentalService.calculate_profit(req)

@router.post("/esg-certificate")
def generate_esg_certificate(req: ESGCertificateRequest):
    """Return an indicative estimate only; this MVP cannot issue a certified ESG document."""
    from backend.app.schemas.environmental import CarbonCalculationRequest
    try:
        estimate = EnvironmentalService.calculate_carbon(
            CarbonCalculationRequest(material_type=req.material_type, tonnage=req.tonnage, emission_factor=req.emission_factor)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "status": "preliminary_estimate_not_a_certificate",
        "issued_to": req.factory_name or "منشأة غير محددة",
        "material_type": req.material_type,
        "tonnage_reported_by_user": req.tonnage,
        "indicative_co2e_estimate_tons": estimate.co2_avoided_tons,
        "methodology": estimate.calculation_basis,
        "notice": "هذا ملخص حسابي أولي وليس شهادة ESG أو شهادة خفض كربوني أو إثباتاً مستقلاً. لا تستخدمه كوثيقة امتثال أو تسويق قبل التحقق من البيانات والمنهجية بواسطة جهة مختصة."
    }
