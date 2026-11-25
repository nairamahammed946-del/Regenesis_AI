from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from backend.app.models.matching import MatchEvent
from backend.app.models.waste import WasteListing
from backend.app.models.user import Factory
from backend.app.core.config import settings

class MatchingService:
    @staticmethod
    def list_matches(db: Session, limit: int = 50) -> List[MatchEvent]:
        stmt = select(MatchEvent).order_by(desc(MatchEvent.score), desc(MatchEvent.created_at))
        if settings.ENVIRONMENT.lower() == "production":
            stmt = (stmt.join(WasteListing, MatchEvent.listing_id == WasteListing.id)
                    .join(Factory, WasteListing.factory_id == Factory.id)
                    .where(Factory.is_verified.is_(True)))
        stmt = stmt.limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def get_legacy_matches(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns the format expected by the legacy frontend."""
        events = MatchingService.list_matches(db, limit)
        out = []
        for e in events:
            l_stmt = select(WasteListing).where(WasteListing.id == e.listing_id)
            c_stmt = select(WasteListing).where(WasteListing.id == e.candidate_id)
            l_res = db.execute(l_stmt)
            c_res = db.execute(c_stmt)
            a = l_res.scalars().first()
            b = c_res.scalars().first()
            if a and b:
                if settings.ENVIRONMENT.lower() == "production" and (not a.factory or not a.factory.is_verified or not b.factory or not b.factory.is_verified):
                    continue
                out.append({
                    "score": e.score,
                    "explanation": e.explanation,
                    "status": e.status,
                    "id": a.legacy_code or f"W-{a.id[:4]}",
                    "title": a.title,
                    "category": a.category,
                    "trade_type": a.trade_type,
                    "qty": a.quantity,
                    "unit": a.unit or "طن",
                    "purity": a.purity,
                    "price": a.price,
                    "currency": a.currency or "EGP",
                    "factory": a.factory_name,
                    "city": a.city,
                    "images": a.images or [],
                    "data_origin": a.data_origin or "user_submitted",
                    "price_basis": a.price_basis or "seller_entered",
                    "bid": b.legacy_code or f"W-{b.id[:4]}",
                    "btitle": b.title,
                    "bcategory": b.category,
                    "btrade_type": b.trade_type,
                    "bfactory": b.factory_name,
                    "bcity": b.city,
                    "bqty": b.quantity,
                    "bunit": b.unit or "طن",
                    "bprice": b.price,
                    "bcurrency": b.currency or "EGP",
                    "bimages": b.images or [],
                    "bdata_origin": b.data_origin or "user_submitted",
                    "bprice_basis": b.price_basis or "seller_entered"
                })
        return out
