import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class EnvironmentalImpact(Base):
    __tablename__ = "environmental_impacts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    factory_id = Column(String(36), ForeignKey("factories.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    material_type = Column(String(100), nullable=False)
    waste_reused_tons = Column(Float, nullable=False, default=0.0)
    waste_diverted_tons = Column(Float, nullable=False, default=0.0)
    co2_avoided_tons = Column(Float, nullable=False, default=0.0)
    trees_equivalent = Column(Float, nullable=False, default=0.0)
    calculation_method = Column(String(255), default="Intergovernmental Circular Economy Emission Factor Benchmark")
    assumptions_applied = Column(JSON, default=dict)
    certificate_number = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    factory = relationship("Factory", back_populates="impact_records")


class SustainabilityScore(Base):
    __tablename__ = "sustainability_scores"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    factory_id = Column(String(36), ForeignKey("factories.id", ondelete="CASCADE"), unique=True, nullable=False)
    overall_score = Column(Float, nullable=False, default=85.0)  # 0 to 100
    waste_reuse_score = Column(Float, default=88.0)
    material_exchange_score = Column(Float, default=82.0)
    waste_diversion_score = Column(Float, default=90.0)
    environmental_impact_score = Column(Float, default=85.0)
    resource_efficiency_score = Column(Float, default=80.0)
    calculation_breakdown = Column(JSON, default=dict)
    badge_level = Column(String(50), default="A+ Platinum Circular Partner")
    last_evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    factory = relationship("Factory", back_populates="sustainability_record")
