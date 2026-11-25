from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import ConfigDict, BaseModel, Field

class PurchaseRequestCreate(BaseModel):
    listing_id: str
    requested_quantity: float = Field(gt=0)
    offered_price: float = Field(ge=0)
    message: Optional[str] = ""

class PurchaseRequestUpdate(BaseModel):
    status: str  # Accepted, Rejected, Countered
    counter_price: Optional[float] = None

class PurchaseRequestResponse(BaseModel):
    id: str
    listing_id: str
    buyer_factory_id: str
    buyer_factory_name: str
    requested_quantity: float
    offered_price: float
    message: Optional[str]
    status: str
    counter_price: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    purchase_request_id: Optional[str] = None
    listing_id: str
    quantity: float
    agreed_price: float = Field(ge=0)
    carrier_name: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    order_number: str
    listing_id: Optional[str]
    seller_factory_id: str
    buyer_factory_id: str
    quantity: float
    agreed_price: float = Field(ge=0)
    total_amount: float
    status: str
    tracking_number: Optional[str]
    carrier_name: Optional[str]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrackingUpdateCreate(BaseModel):
    checkpoint_name: str
    location: str
    status_update: str
    notes: Optional[str] = ""
    verified_by: Optional[str] = None

class TrackingRecordResponse(BaseModel):
    id: str
    order_id: str
    checkpoint_name: str
    location: str
    status_update: str
    notes: Optional[str]
    verified_by: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionResponse(BaseModel):
    id: str
    order_id: str
    amount: float
    currency: str
    transaction_type: str
    status: str
    payment_method: str
    reference_number: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
