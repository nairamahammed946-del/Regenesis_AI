from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, desc
from backend.app.models.waste import WasteListing, WasteCategory
from backend.app.schemas.waste import WasteListingCreate
from backend.app.ai.matching_engine import SmartMatchingEngine
from backend.app.models.matching import MatchEvent
from backend.app.models.user import Factory
from backend.app.core.config import settings

class ListingService:
    @staticmethod
    def get_by_id(db: Session, listing_id: str) -> Optional[WasteListing]:
        stmt = select(WasteListing).where(or_(
            WasteListing.id == listing_id,
            WasteListing.legacy_code == listing_id
        ))
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def list_listings(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        trade_type: Optional[str] = None,
        search: Optional[str] = None,
        city: Optional[str] = None
    ) -> List[WasteListing]:
        stmt = select(WasteListing).order_by(desc(WasteListing.created_at))
        if settings.ENVIRONMENT.lower() == "production":
            stmt = stmt.join(Factory, WasteListing.factory_id == Factory.id).where(Factory.is_verified.is_(True))
        if category and category != "ALL":
            stmt = stmt.where(WasteListing.category == category)
        if trade_type and trade_type != "ALL":
            if "عرض" in trade_type or "supply" in trade_type.lower():
                stmt = stmt.where(WasteListing.trade_type.ilike("%عرض%"))
            elif "طلب" in trade_type or "demand" in trade_type.lower():
                stmt = stmt.where(WasteListing.trade_type.ilike("%طلب%"))
        if city and city != "ALL":
            stmt = stmt.where(WasteListing.city.ilike(f"%{city}%"))
        if search:
            stmt = stmt.where(or_(
                WasteListing.title.ilike(f"%{search}%"),
                WasteListing.factory_name.ilike(f"%{search}%"),
                WasteListing.city.ilike(f"%{search}%"),
                WasteListing.description.ilike(f"%{search}%")
            ))
        stmt = stmt.offset(skip).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def create(
        db: Session,
        listing_in: WasteListingCreate,
        factory_id: Optional[str] = None
    ) -> WasteListing:
        count_stmt = select(WasteListing)
        all_res = db.execute(count_stmt)
        next_num = len(all_res.scalars().all()) + 901

        category_row = db.execute(select(WasteCategory).where(WasteCategory.name == listing_in.category)).scalars().first()
        listing = WasteListing(
            legacy_code=f"W-{next_num}",
            title=listing_in.title,
            category=listing_in.category,
            category_id=category_row.id if category_row else None,
            factory_id=factory_id,
            factory_name=listing_in.factory_name or "مصنع غير مسمى",
            city=listing_in.city,
            trade_type=listing_in.trade_type,
            quantity=listing_in.quantity,
            unit=listing_in.unit,
            purity=listing_in.purity,
            price=listing_in.price,
            currency=listing_in.currency,
            description=listing_in.description or "",
            images=listing_in.images or [],
            video_path=listing_in.video_path,
            data_origin="user_submitted",
            price_basis="سعر أدخله ناشر الإعلان؛ لم يتم التحقق منه من المنصة",
            images_are_illustrative=False,
            lab_verified=False,
            status="Active",
            ai_match_hint="تنتظر المطابقة الأولية والتحقق من بيانات المنشأة"
        )
        db.add(listing)
        db.flush()

        # Run automated real-time matching against existing opposite listings
        candidates = ListingService.list_listings(db, limit=50)
        for cand in candidates:
            if cand.id != listing.id and cand.category == listing.category:
                s_dict = {
                    "category": listing.category,
                    "trade_type": listing.trade_type,
                    "quantity": listing.quantity,
                    "purity": listing.purity,
                    "city": listing.city,
                    "price": listing.price
                }
                c_dict = {
                    "category": cand.category,
                    "trade_type": cand.trade_type,
                    "quantity": cand.quantity,
                    "purity": cand.purity,
                    "city": cand.city,
                    "price": cand.price
                }
                score, details = SmartMatchingEngine.score_listings(s_dict, c_dict)
                if score >= 40.0:
                    evt = MatchEvent(
                        listing_id=listing.id,
                        candidate_id=cand.id,
                        score=score,
                        explanation=details["explanation"],
                        category_score=details["breakdown"]["category_score"],
                        trade_score=details["breakdown"]["trade_score"],
                        quantity_score=details["breakdown"]["quantity_score"],
                        purity_score=details["breakdown"]["purity_score"],
                        location_score=details["breakdown"]["location_score"],
                        price_score=details["breakdown"]["price_score"],
                        reasons=details["reasons"],
                        missing_info=details["missing_info"],
                        suggested_steps=details["suggested_steps"]
                    )
                    db.add(evt)

        return listing

    @staticmethod
    def to_legacy_dict(listing: WasteListing) -> Dict[str, Any]:
        """Convert modern SQLAlchemy listing to exact legacy frontend dictionary shape."""
        # No verified lifecycle methodology is bundled; avoid emitting assumed CO2 factors.
        category_factor = 0.0

        return {
            "id": listing.legacy_code or f"W-{listing.id[:4]}",
            "db_id": listing.id,
            "title": listing.title,
            "category": listing.category,
            "tradeType": listing.trade_type,
            "qty": float(listing.quantity),
            "unit": listing.unit or "طن",
            "purity": float(listing.purity),
            "price": float(listing.price),
            "currency": listing.currency or "EGP",
            "factory": listing.factory_name,
            "factory_id": listing.factory_id,
            "city": listing.city,
            "desc": listing.description or "",
            "images": listing.images or [],
            "images_are_illustrative": bool(listing.images_are_illustrative),
            "data_origin": listing.data_origin or "user_submitted",
            "price_basis": listing.price_basis or "seller_entered",
            "lab_verified": bool(listing.lab_verified),
            "status": listing.status,
            "aiMatch": listing.ai_match_hint or "مطابقة أولية؛ تحقق من المواصفات",
            "co2_factor": category_factor
        }
