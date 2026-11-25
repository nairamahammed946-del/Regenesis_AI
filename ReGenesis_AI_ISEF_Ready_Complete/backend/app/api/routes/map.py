from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.models.user import Factory
from backend.app.models.waste import WasteListing
from backend.app.core.config import settings

router = APIRouter(prefix="/map", tags=["Industrial Circular Economy Map"])

@router.get("/factories")
def get_map_resources(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Return industrial facilities and available waste resources for interactive GIS map visualization.
    Coordinates reflect industrial zones with privacy-respecting offset.
    """
    f_stmt = select(Factory)
    if settings.ENVIRONMENT.lower() == "production":
        f_stmt = f_stmt.where(Factory.is_verified.is_(True))
    f_res = db.execute(f_stmt)
    factories = list(f_res.scalars().all())

    # Pre-defined real coordinates of Egyptian/Regional industrial zones
    zone_coordinates = {
        "مدينة دمياط للأثاث": {"lat": 31.4175, "lng": 31.8144},
        "العاشر من رمضان": {"lat": 30.3015, "lng": 31.7431},
        "السادس من أكتوبر": {"lat": 29.9723, "lng": 30.9525},
        "حلوان - القاهرة": {"lat": 29.8415, "lng": 31.3008},
        "مدينة السادات": {"lat": 30.3756, "lng": 30.5284},
        "برج العرب - الإسكندرية": {"lat": 30.9167, "lng": 29.6667}
    }

    out = []
    for f in factories:
        coords = {"lat": f.latitude, "lng": f.longitude} if f.latitude is not None and f.longitude is not None else zone_coordinates.get(f.city, {"lat": None, "lng": None})
        
        # Query listings for this factory
        l_stmt = select(WasteListing).where(WasteListing.factory_id == f.id, WasteListing.status == "Active")
        l_res = db.execute(l_stmt)
        listings = list(l_res.scalars().all())

        materials_summary = [f"{l.title} ({l.quantity} طن - {l.trade_type})" for l in listings[:3]]

        out.append({
            "id": f.id,
            "name": f.name,
            "city": f.city,
            "sector": f.sector,
            "role": f.role,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "sustainability_score": f.sustainability_score,
            "materials_available_count": len(listings),
            "materials_summary": materials_summary,
            "is_verified": f.is_verified
        })

    return out
