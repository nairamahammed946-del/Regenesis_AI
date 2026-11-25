from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from backend.app.models.user import Factory
from backend.app.schemas.user import FactoryCreate, FactoryUpdate
from backend.app.core.config import settings

class FactoryService:
    @staticmethod
    def get_by_id(db: Session, factory_id: str) -> Optional[Factory]:
        stmt = select(Factory).where(Factory.id == factory_id)
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Factory]:
        stmt = select(Factory).where(Factory.name == name)
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[Factory]:
        stmt = select(Factory).where(Factory.owner_id == user_id)
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def create(db: Session, factory_in: FactoryCreate, owner_id: Optional[str] = None) -> Factory:
        existing = FactoryService.get_by_name(db, factory_in.name)
        if existing:
            if owner_id and existing.owner_id == owner_id:
                return existing
            raise ValueError("اسم المنشأة مسجل بالفعل؛ لا يمكن ربط حساب جديد بسجل منشأة قائم تلقائياً.")

        factory = Factory(
            name=factory_in.name,
            owner_id=owner_id,
            sector=factory_in.sector,
            role=factory_in.role,
            city=factory_in.city,
            address=factory_in.address,
            latitude=factory_in.latitude,
            longitude=factory_in.longitude,
            contact_email=factory_in.contact_email,
            contact_phone=factory_in.contact_phone,
            description=factory_in.description,
            sustainability_score=0.0,
            is_verified=False,
            data_origin="user_submitted"
        )
        db.add(factory)
        db.flush()
        return factory

    @staticmethod
    def list_factories(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        sector: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Factory]:
        stmt = select(Factory)
        if settings.ENVIRONMENT.lower() == "production":
            stmt = stmt.where(Factory.is_verified.is_(True))
        if sector and sector != "ALL":
            stmt = stmt.where(Factory.sector == sector)
        if city and city != "ALL":
            stmt = stmt.where(Factory.city.ilike(f"%{city}%"))
        if search:
            stmt = stmt.where(or_(
                Factory.name.ilike(f"%{search}%"),
                Factory.city.ilike(f"%{search}%"),
                Factory.sector.ilike(f"%{search}%")
            ))
        stmt = stmt.offset(skip).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())
