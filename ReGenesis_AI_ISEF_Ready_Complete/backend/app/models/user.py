import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    factories = relationship("Factory", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Factory(Base):
    __tablename__ = "factories"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    sector = Column(String(100), nullable=False, default="غير محدد")  # Wood, Plastic, Metals, Chemicals, Textiles, Glass
    role = Column(String(100), nullable=False, default="Waste Producer")  # Producer, Consumer, Recycler, R&D
    city = Column(String(255), nullable=False, default="غير محدد")
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    sustainability_score = Column(Float, default=0.0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    # Provenance prevents public directory entries and simulated demo profiles
    # from being mistaken for verified commercial partners.
    data_origin = Column(String(50), default="user_submitted", nullable=False, index=True)
    source_name = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_date = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("User", back_populates="factories")
    listings = relationship("WasteListing", back_populates="factory", cascade="all, delete-orphan")
    sent_requests = relationship("PurchaseRequest", foreign_keys="PurchaseRequest.buyer_factory_id", back_populates="buyer_factory")
    seller_orders = relationship("Order", foreign_keys="Order.seller_factory_id", back_populates="seller_factory")
    buyer_orders = relationship("Order", foreign_keys="Order.buyer_factory_id", back_populates="buyer_factory")
    analyses = relationship("MaterialAnalysis", back_populates="factory")
    impact_records = relationship("EnvironmentalImpact", back_populates="factory")
    sustainability_record = relationship("SustainabilityScore", back_populates="factory", uselist=False)
