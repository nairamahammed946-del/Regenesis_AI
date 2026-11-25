import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(TEST_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.core.database import Base
from backend.app.models.user import Factory
from backend.app.models.marketplace import Transaction, WasteTrackingRecord
from backend.app.schemas.waste import WasteListingCreate
from backend.app.schemas.marketplace import PurchaseRequestCreate, OrderCreate
from backend.app.services.listing_service import ListingService
from backend.app.services.marketplace_service import MarketplaceService
from backend.app.core.config import settings
from backend.app.ai.web_search import needs_web_search


def test_marketplace_never_marks_unpaid_order_as_paid_or_shipped():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    try:
        seller = Factory(name="Seller", sector="بلاستيك", role="Waste Producer", city="Giza", is_verified=False)
        buyer = Factory(name="Buyer", sector="بلاستيك", role="Raw Material Buyer", city="Giza", is_verified=False)
        db.add_all([seller, buyer]); db.flush()
        listing = ListingService.create(db, WasteListingCreate(
            title="HDPE flakes", category="بلاستيك", trade_type="عرض (توفر مخلفات)",
            quantity=10, purity=90, price=100, city="Giza", factory_name="Seller"
        ), factory_id=seller.id)
        request = MarketplaceService.create_purchase_request(db, PurchaseRequestCreate(
            listing_id=listing.id, requested_quantity=5, offered_price=95
        ), buyer)
        request = MarketplaceService.update_purchase_request(db, request.id, type("Update", (), {"status": "Accepted", "counter_price": None})(), seller)
        order = MarketplaceService.create_order(db, OrderCreate(
            purchase_request_id=request.id, listing_id=listing.id, quantity=5, agreed_price=95
        ), seller_factory_id=seller.id, buyer_factory_id=buyer.id)
        tx = db.query(Transaction).filter(Transaction.order_id == order.id).one()
        track = db.query(WasteTrackingRecord).filter(WasteTrackingRecord.order_id == order.id).one()
        assert order.status == "Pending_Contract_Confirmation"
        assert tx.status == "Pending"
        assert tx.currency == "UNSPECIFIED"
        assert track.verified_by is None
        assert "Awaiting Dispatch" in track.status_update
    finally:
        db.close(); engine.dispose()


def test_web_search_intent_detection():
    assert needs_web_search("ابحث عن مصانع تدوير البلاستيك في مصر")
    assert not needs_web_search("اشرح لي الفرق بين PET وHDPE")


def test_production_marketplace_hides_unverified_factory_listings(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    try:
        verified = Factory(name="Verified", sector="بلاستيك", role="Waste Producer", city="Giza", is_verified=True)
        pending = Factory(name="Pending", sector="بلاستيك", role="Waste Producer", city="Giza", is_verified=False)
        db.add_all([verified, pending]); db.flush()
        for factory in (verified, pending):
            ListingService.create(db, WasteListingCreate(
                title=f"Listing {factory.name}", category="بلاستيك", trade_type="عرض (توفر مخلفات)",
                quantity=2, purity=90, price=10, city="Giza", factory_name=factory.name
            ), factory_id=factory.id)
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        visible = ListingService.list_listings(db)
        assert len(visible) == 1
        assert visible[0].factory_id == verified.id
    finally:
        db.close(); engine.dispose()
