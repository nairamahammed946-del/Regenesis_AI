from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.waste import WasteListingCreate, WasteListingResponse
from backend.app.services.listing_service import ListingService
from backend.app.core.config import settings
from backend.app.api.deps import get_current_user
from backend.app.models.user import User

router = APIRouter(prefix="/listings", tags=["Waste Listings & Marketplace"])

@router.get("", response_model=List[WasteListingResponse])
def list_listings(
    category: Optional[str] = None,
    trade_type: Optional[str] = None,
    search: Optional[str] = None,
    city: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Browse active waste listings and material requests with real-time filters."""
    listings = ListingService.list_listings(db, skip, limit, category, trade_type, search, city)
    return [WasteListingResponse.model_validate(l) for l in listings]

@router.get("/{listing_id}", response_model=WasteListingResponse)
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    """Retrieve full details of a specific waste listing."""
    listing = ListingService.get_by_id(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="إعلان المادة غير موجود")
    if settings.ENVIRONMENT.lower() == "production" and (not listing.factory or not listing.factory.is_verified):
        raise HTTPException(status_code=404, detail="الإعلان غير متاح للعامة قبل التحقق من المنشأة")
    return WasteListingResponse.model_validate(listing)

@router.post("", response_model=WasteListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(
    listing_in: WasteListingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publish a new waste supply or material demand listing with automatic AI matching."""
    factory_id = None
    if current_user.factories:
        factory_id = current_user.factories[0].id
        if not listing_in.factory_name:
            listing_in.factory_name = current_user.factories[0].name
    
    listing = ListingService.create(db, listing_in, factory_id=factory_id)
    return WasteListingResponse.model_validate(listing)
