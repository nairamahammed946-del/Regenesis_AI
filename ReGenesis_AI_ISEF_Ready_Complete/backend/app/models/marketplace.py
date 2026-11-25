import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    listing_id = Column(String(36), ForeignKey("waste_listings.id", ondelete="CASCADE"), nullable=False)
    buyer_factory_id = Column(String(36), ForeignKey("factories.id", ondelete="CASCADE"), nullable=False)
    buyer_factory_name = Column(String(255), nullable=False)
    requested_quantity = Column(Float, nullable=False)
    offered_price = Column(Float, nullable=False)
    message = Column(Text, nullable=True)
    status = Column(String(50), default="Pending", index=True)  # Pending, Accepted, Rejected, Countered, Completed
    counter_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    listing = relationship("WasteListing", back_populates="purchase_requests")
    buyer_factory = relationship("Factory", foreign_keys=[buyer_factory_id], back_populates="sent_requests")
    order = relationship("Order", back_populates="purchase_request", uselist=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    purchase_request_id = Column(String(36), ForeignKey("purchase_requests.id", ondelete="SET NULL"), nullable=True)
    listing_id = Column(String(36), ForeignKey("waste_listings.id", ondelete="SET NULL"), nullable=True)
    seller_factory_id = Column(String(36), ForeignKey("factories.id", ondelete="CASCADE"), nullable=False)
    buyer_factory_id = Column(String(36), ForeignKey("factories.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Float, nullable=False)
    agreed_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default="Confirmed", index=True)  # Confirmed, Processing, InTransit, Delivered, Completed, Cancelled
    tracking_number = Column(String(100), nullable=True)
    carrier_name = Column(String(150), nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    purchase_request = relationship("PurchaseRequest", back_populates="order")
    listing = relationship("WasteListing", back_populates="orders")
    seller_factory = relationship("Factory", foreign_keys=[seller_factory_id], back_populates="seller_orders")
    buyer_factory = relationship("Factory", foreign_keys=[buyer_factory_id], back_populates="buyer_orders")
    transactions = relationship("Transaction", back_populates="order", cascade="all, delete-orphan")
    tracking_updates = relationship("WasteTrackingRecord", back_populates="order", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(20), default="USD")
    transaction_type = Column(String(50), default="Escrow_Payment")  # Escrow_Payment, Release, Refund
    status = Column(String(50), default="Completed")  # Pending, Completed, Failed
    payment_method = Column(String(100), default="B2B Wire / Commercial Letter")
    reference_number = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="transactions")


class WasteTrackingRecord(Base):
    __tablename__ = "waste_tracking_records"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    checkpoint_name = Column(String(200), nullable=False)
    location = Column(String(255), nullable=False)
    status_update = Column(String(100), nullable=False)  # Loaded, Weighbridge_Verified, Dispatched, In_Transit, Received, Quality_Inspected
    notes = Column(Text, nullable=True)
    verified_by = Column(String(150), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="tracking_updates")
