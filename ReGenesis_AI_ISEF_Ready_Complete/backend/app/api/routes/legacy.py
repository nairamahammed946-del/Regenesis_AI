from typing import List, Dict, Any
import os, uuid
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.waste import LegacyListingIn, LegacyListingOut
from backend.app.schemas.dashboard import AdvisorIn, AdvisorOut
from backend.app.schemas.matching import LegacyMatchOut
from backend.app.services.listing_service import ListingService
from backend.app.services.matching_service import MatchingService
from backend.app.ai.advisor import AIAdvisor
from backend.app.ai.matching_engine import SmartMatchingEngine
from backend.app.core.config import settings
from backend.app.schemas.waste import WasteListingCreate
from backend.app.api.deps import get_current_user
from backend.app.models.user import User, Factory
from backend.app.api.deps import get_current_user_optional

router = APIRouter(tags=["Legacy Frontend Compatibility (Unversioned /api/)"])

@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Health check endpoint maintaining exact backward compatibility."""
    listings = ListingService.list_listings(db)
    return {
        "status": "ok",
        "service": "ReGenesis AI Professional Enterprise",
        "version": settings.APP_VERSION,
        "database": "connected",
        "listings": len(listings)
    }

@router.get("/listings")
def get_legacy_listings(db: Session = Depends(get_db)):
    """Return listings in the exact JSON schema expected by the original frontend."""
    listings = ListingService.list_listings(db)
    return [ListingService.to_legacy_dict(l) for l in listings]

@router.post("/listings")
def create_legacy_listing(x: LegacyListingIn, current_user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Accept listing submissions from signed-in users or local read/write demo mode."""
    if current_user is None and (not settings.DEMO_MODE or settings.ENVIRONMENT.lower() == "production"):
        raise HTTPException(status_code=401, detail="يرجى تسجيل الدخول لنشر إعلان.")
    modern_create = WasteListingCreate(
        title=x.title,
        category=x.category,
        trade_type=x.tradeType,
        quantity=x.qty,
        purity=x.purity,
        price=x.price,
        city=x.city,
        description=x.desc or "",
        images=x.images or [],
        factory_name=x.factory
    )
    factory = current_user.factories[0] if current_user and current_user.factories else None
    if current_user is None and settings.DEMO_MODE and settings.ENVIRONMENT.lower() != "production":
        factory = db.query(Factory).filter(Factory.name == "منشأة زائر وضع العرض التجريبي").first()
        if not factory:
            factory = Factory(
                name="منشأة زائر وضع العرض التجريبي", sector=x.category, role="Demo Contributor", city=x.city,
                description="ملف محلي مؤقت لزائر العرض؛ ليس منشأة تجارية حقيقية.",
                data_origin="demo_synthetic", is_verified=False,
            )
            db.add(factory); db.flush()
        modern_create.factory_name = factory.name
    if factory and not modern_create.factory_name:
        modern_create.factory_name = factory.name
    new_listing = ListingService.create(db, modern_create, factory_id=factory.id if factory else None)
    if current_user is None and settings.DEMO_MODE and settings.ENVIRONMENT.lower() != "production":
        new_listing.data_origin = "demo_synthetic"
        new_listing.price_basis = "قيمة أدخلها زائر في وضع العرض؛ لم يتم التحقق منها"
    
    # Calculate top matches
    all_listings = ListingService.list_listings(db, limit=50)
    matches = []
    new_dict = ListingService.to_legacy_dict(new_listing)
    
    for other in all_listings:
        if other.id != new_listing.id and other.category == new_listing.category:
            other_dict = ListingService.to_legacy_dict(other)
            score, details = SmartMatchingEngine.score_listings(new_dict, other_dict)
            if score >= 35.0:
                matches.append({
                    "listing": other_dict,
                    "score": score,
                    "reason": details["explanation"]
                })
    
    matches.sort(key=lambda z: z["score"], reverse=True)
    return {
        "listing": new_dict,
        "matches": matches[:5]
    }

@router.get("/matches")
def get_legacy_matches(db: Session = Depends(get_db)):
    """Return matches in the exact format consumed by the original frontend table."""
    return MatchingService.get_legacy_matches(db, limit=100)

@router.post("/uploads/waste-images")
async def upload_waste_images(files: List[UploadFile] = File(...), current_user: User | None = Depends(get_current_user_optional)):
    """Upload images for signed-in listings or local demo submissions."""
    if current_user is None and (not settings.DEMO_MODE or settings.ENVIRONMENT.lower() == "production"):
        raise HTTPException(status_code=401, detail="يرجى تسجيل الدخول لرفع صور الإعلان.")
    if not files or len(files) > 6:
        raise HTTPException(status_code=400, detail="ارفع من صورة واحدة إلى 6 صور كحد أقصى.")
    allowed={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/bmp":".bmp"}
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    urls=[]
    for upload in files:
        if upload.content_type not in allowed:
            raise HTTPException(status_code=415, detail="الصيغ المدعومة: JPG وPNG وWEBP وBMP.")
        raw=await upload.read(settings.MAX_UPLOAD_SIZE+1)
        if len(raw)>settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="إحدى الصور تتجاوز الحد الأقصى للحجم.")
        try:
            from io import BytesIO
            img=Image.open(BytesIO(raw)); img.verify()
        except (UnidentifiedImageError, OSError):
            raise HTTPException(status_code=400, detail="أحد الملفات المرفوعة ليس صورة سليمة.")
        filename=f"listing-{uuid.uuid4().hex}{allowed[upload.content_type]}"
        with open(os.path.join(settings.UPLOAD_DIR, filename), "wb") as out: out.write(raw)
        urls.append("/uploads/"+filename)
    return {"images": urls, "count": len(urls)}

@router.post("/advisor")
async def legacy_advisor(x: AdvisorIn, current_user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Legacy frontend assistant; anonymous read-only access is limited to local demo mode."""
    if current_user is None and (not settings.DEMO_MODE or settings.ENVIRONMENT.lower() == "production"):
        raise HTTPException(status_code=401, detail="يرجى تسجيل الدخول للوصول إلى المساعد.")
    listings = ListingService.list_listings(db, limit=500)
    list_dicts = [ListingService.to_legacy_dict(l) for l in listings]
    factories = db.query(Factory).limit(200).all()
    factory_rows = [{"name":f.name,"sector":f.sector,"role":f.role,"city":f.city,"description":f.description,
                     "is_verified":f.is_verified,"data_origin":f.data_origin,"source_name":f.source_name,
                     "source_url":f.source_url,"source_date":f.source_date} for f in factories]
    result = await AIAdvisor.answer(x.message, list_dicts, x.history or [], factory_records=factory_rows)
    return {
        "answer": result["answer"],
        "records_considered": result["records_considered"],
        "mode": result["mode"]
    }
