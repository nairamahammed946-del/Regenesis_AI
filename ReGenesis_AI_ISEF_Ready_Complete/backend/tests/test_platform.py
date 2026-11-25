import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test database
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TEST_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.app.core.database import Base
from backend.app.models.waste import WasteListing
from backend.app.models.user import Factory, User
from backend.app.services.auth_service import AuthService
from backend.app.services.factory_service import FactoryService
from backend.app.services.listing_service import ListingService
from backend.app.services.environmental_service import EnvironmentalService
from backend.app.ai.matching_engine import SmartMatchingEngine
from backend.app.ai.waste_scanner import WasteScanner
from backend.app.ai.reuse_recommender import ReuseRecommender
from backend.app.ai.waste_to_product import WasteToProductEngine
from backend.app.ai.demand_predictor import DemandPredictor
from backend.app.ai.negotiation_assistant import SmartNegotiationAssistant
from backend.app.schemas.user import UserCreate, UserLogin, FactoryCreate
from backend.app.schemas.waste import WasteListingCreate
from backend.app.schemas.environmental import CarbonCalculationRequest, ProfitCalculationRequest

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)
    session = TestingSessionLocal()
    yield session
    session.close()

def test_user_registration_and_auth(db_session):
    user_in = UserCreate(email="test@factory.com", password="SecurePassword123!", full_name="مهندس أحمد", phone="01012345678")
    user = AuthService.register(db_session, user_in)
    assert user.id is not None
    assert user.email == "test@factory.com"
    
    # Authenticate
    auth_user = AuthService.authenticate(db_session, UserLogin(email="test@factory.com", password="SecurePassword123!"))
    assert auth_user.id == user.id

def test_factory_creation_and_listing(db_session):
    factory_in = FactoryCreate(name="مصنع النقاء للأثاث", sector="خشب", role="Waste Producer", city="دمياط")
    factory = FactoryService.create(db_session, factory_in)
    assert factory.id is not None
    assert factory.name == "مصنع النقاء للأثاث"

    listing_in = WasteListingCreate(
        title="نشارة زان ناعمة", category="خشب", trade_type="عرض (توفر مخلفات)",
        quantity=30.0, purity=95.0, price=45.0, city="دمياط", factory_name=factory.name
    )
    listing = ListingService.create(db_session, listing_in, factory_id=factory.id)
    assert listing.id is not None
    assert listing.quantity == 30.0

def test_explainable_matching_algorithm():
    supply = {"category": "خشب", "trade_type": "عرض (توفر مخلفات)", "quantity": 25.0, "purity": 95.0, "price": 40.0, "city": "دمياط"}
    demand = {"category": "خشب", "trade_type": "طلب (احتياج خامة)", "quantity": 30.0, "purity": 90.0, "price": 42.0, "city": "دمياط"}
    
    score, details = SmartMatchingEngine.score_listings(supply, demand)
    assert score >= 85.0
    assert "reasons" in details
    assert len(details["reasons"]) > 0
    assert details["breakdown"]["category_score"] == 100.0

def test_carbon_and_profit_calculators():
    with pytest.raises(ValueError):
        EnvironmentalService.calculate_carbon(CarbonCalculationRequest(material_type="خشب", tonnage=50.0))
    c_req = CarbonCalculationRequest(material_type="خشب", tonnage=50.0, emission_factor=1.2)
    c_res = EnvironmentalService.calculate_carbon(c_req)
    assert c_res.co2_avoided_tons == 60.0
    assert c_res.trees_equivalent is None
    assert "سيناريو" in c_res.disclaimer

    p_req = ProfitCalculationRequest(
        material_type="بلاستيك", quantity_tons=20.0, waste_selling_price_per_ton=320.0,
        virgin_material_price_per_ton=650.0, processing_cost_per_ton=15.0, transport_distance_km=20.0
    )
    p_res = EnvironmentalService.calculate_profit(p_req)
    assert p_res.potential_selling_revenue == 6400.0
    assert p_res.net_economic_benefit > 0

def test_ai_scanner_and_engines():
    # 1. Reuse Recommender
    recs = ReuseRecommender.get_recommendations("خشب")
    assert len(recs) > 0
    assert "pathway_name" in recs[0]

    # 2. Waste to Product
    prods = WasteToProductEngine.get_products("بلاستيك")
    assert len(prods) > 0
    assert "estimated_value_per_ton" in prods[0]

    # 3. Negotiation Assistant
    neg = SmartNegotiationAssistant.analyze_price("ألومنيوم", 10.0, 98.0, 1450.0, "حلوان")
    assert neg["fair_market_price"] is None
    assert neg["data_status"] == "no_comparable_listings"
    assert len(neg["negotiation_tips"]) > 0

    # 4. Demand Predictor
    listings = [{"category": "خشب", "trade_type": "عرض", "quantity": 25.0}]
    pred = DemandPredictor.predict(listings)
    assert len(pred["predictions"]) > 0
