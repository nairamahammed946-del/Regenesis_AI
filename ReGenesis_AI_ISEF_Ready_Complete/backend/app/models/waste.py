import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class WasteCategory(Base):
    __tablename__ = "waste_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    name_en = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    co2_factor = Column(Float, nullable=False, default=2.0)  # tons CO2 avoided per ton recycled
    icon = Column(String(50), default="fa-recycle")

    listings = relationship("WasteListing", back_populates="category_rel")


class WasteListing(Base):
    __tablename__ = "waste_listings"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    legacy_code = Column(String(50), nullable=True, index=True)  # e.g. W-901
    title = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)  # خشب, بلاستيك, معادن, مواد كيميائية, زجاج, نسيج
    category_id = Column(Integer, ForeignKey("waste_categories.id"), nullable=True)
    factory_id = Column(String(36), ForeignKey("factories.id", ondelete="CASCADE"), nullable=True)
    factory_name = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    trade_type = Column(String(100), nullable=False, default="عرض (توفر مخلفات)")  # عرض / طلب
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="طن")
    purity = Column(Float, nullable=False, default=90.0)  # 0 to 100%
    price = Column(Float, nullable=False, default=0.0)  # entered/illustrative price per unit; currency field is explicit
    currency = Column(String(20), default="EGP")
    description = Column(Text, nullable=True)
    images = Column(JSON, default=list)  # list of uploaded file paths or URLs
    video_path = Column(String(500), nullable=True)
    lab_verified = Column(Boolean, default=False)
    status = Column(String(50), default="Active", index=True)  # Active, Reserved, Sold, Inactive
    ai_match_hint = Column(String(255), nullable=True)
    # Provenance and price basis are explicit; demo sample data must never look like a live quotation.
    data_origin = Column(String(50), default="user_submitted", nullable=False, index=True)
    price_basis = Column(String(120), default="seller_entered", nullable=False)
    images_are_illustrative = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    category_rel = relationship("WasteCategory", back_populates="listings")
    factory = relationship("Factory", back_populates="listings")
    purchase_requests = relationship("PurchaseRequest", back_populates="listing", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="listing")
    analyses = relationship("MaterialAnalysis", back_populates="listing")


class MaterialAnalysis(Base):
    __tablename__ = "material_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    factory_id = Column(String(36), ForeignKey("factories.id", ondelete="CASCADE"), nullable=True)
    listing_id = Column(String(36), ForeignKey("waste_listings.id", ondelete="SET NULL"), nullable=True)
    image_paths = Column(JSON, default=list)
    video_path = Column(String(500), nullable=True)
    
    # 12-factor structured analysis report as requested
    predicted_category = Column(String(100), nullable=False)
    predicted_material_type = Column(String(150), nullable=False)
    visual_characteristics = Column(JSON, default=list)
    color = Column(String(100), nullable=True)
    shape = Column(String(100), nullable=True)
    approximate_size = Column(String(100), nullable=True)
    visible_contamination = Column(Text, nullable=True)
    material_condition = Column(String(100), nullable=True)  # Excellent, Good, Degraded, Scrap
    potential_applications = Column(JSON, default=list)
    possible_recycling_methods = Column(JSON, default=list)
    suggested_reuse_opportunities = Column(JSON, default=list)
    confidence_score = Column(Float, nullable=False, default=0.92)
    testing_recommendations = Column(JSON, default=list)
    
    # Transparency fields
    analysis_mode = Column(String(50), default="AI_RuleBased_VisionEngine")  # Real CV model or Expert Feature Extraction
    lab_verification_status = Column(String(50), default="Pending Laboratory Validation")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    factory = relationship("Factory", back_populates="analyses")
    listing = relationship("WasteListing", back_populates="analyses")


class MaterialProperty(Base):
    __tablename__ = "material_properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_name = Column(String(150), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=False)
    density_g_cm3 = Column(Float, nullable=True)
    melting_point_c = Column(Float, nullable=True)
    tensile_strength_mpa = Column(Float, nullable=True)
    moisture_content_pct = Column(Float, nullable=True)
    flammability = Column(String(100), nullable=True)
    recommended_storage = Column(Text, nullable=True)
    handling_precautions = Column(Text, nullable=True)
    co2_factor = Column(Float, default=2.5)
