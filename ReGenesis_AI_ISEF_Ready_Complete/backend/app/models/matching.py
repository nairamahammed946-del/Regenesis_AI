import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class MatchEvent(Base):
    __tablename__ = "match_events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    listing_id = Column(String(36), ForeignKey("waste_listings.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(String(36), ForeignKey("waste_listings.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    
    # Detailed factor scores
    category_score = Column(Float, default=1.0)
    trade_score = Column(Float, default=1.0)
    quantity_score = Column(Float, default=1.0)
    purity_score = Column(Float, default=1.0)
    location_score = Column(Float, default=1.0)
    price_score = Column(Float, default=1.0)
    
    # Explainable AI fields
    reasons = Column(JSON, default=list)
    missing_info = Column(JSON, default=list)
    suggested_steps = Column(JSON, default=list)
    
    status = Column(String(50), default="New")  # New, Viewed, Contacted, Rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    listing = relationship("WasteListing", foreign_keys=[listing_id])
    candidate = relationship("WasteListing", foreign_keys=[candidate_id])
