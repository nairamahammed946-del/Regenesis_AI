from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.user import FactoryCreate, FactoryResponse, FactoryUpdate
from backend.app.services.factory_service import FactoryService
from backend.app.services.environmental_service import EnvironmentalService
from backend.app.schemas.environmental import SustainabilityScoreResponse
from backend.app.api.deps import get_current_user
from backend.app.models.user import User, Factory
from backend.app.core.config import settings

router = APIRouter(prefix="/factories", tags=["Industrial Facilities"])

@router.get("", response_model=List[FactoryResponse])
def list_factories(
    sector: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List participating industrial factories with filters."""
    factories = FactoryService.list_factories(db, skip, limit, sector, city, search)
    return [FactoryResponse.model_validate(f) for f in factories]

@router.get("/{factory_id}", response_model=FactoryResponse)
def get_factory(factory_id: str, db: Session = Depends(get_db)):
    """Get single factory profile and verification status."""
    factory = FactoryService.get_by_id(db, factory_id)
    if not factory or (settings.ENVIRONMENT.lower() == "production" and not factory.is_verified):
        raise HTTPException(status_code=404, detail="المنشأة غير موجودة أو لم يتم التحقق منها")
    return FactoryResponse.model_validate(factory)

@router.post("", response_model=FactoryResponse, status_code=status.HTTP_201_CREATED)
def create_factory(
    factory_in: FactoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a new factory facility under current user."""
    if FactoryService.get_by_name(db, factory_in.name):
        raise HTTPException(status_code=409, detail="اسم المنشأة مسجل بالفعل")
    factory = FactoryService.create(db, factory_in, owner_id=current_user.id)
    return FactoryResponse.model_validate(factory)

@router.get("/{factory_id}/sustainability", response_model=SustainabilityScoreResponse)
def get_sustainability_score(factory_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed ESG sustainability scoring and methodology."""
    return EnvironmentalService.get_or_calculate_sustainability(db, factory_id)

@router.post("/{factory_id}/verify", response_model=FactoryResponse)
def verify_factory(
    factory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a factory verified only after an administrator completes external checks."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="صلاحية مسؤول النظام مطلوبة")
    factory = FactoryService.get_by_id(db, factory_id)
    if not factory:
        raise HTTPException(status_code=404, detail="المنشأة غير موجودة")
    factory.is_verified = True
    db.add(factory)
    db.flush()
    return FactoryResponse.model_validate(factory)
