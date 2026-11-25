from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.marketplace import (
    PurchaseRequestCreate, PurchaseRequestUpdate, PurchaseRequestResponse,
    OrderCreate, OrderResponse, TrackingUpdateCreate, TrackingRecordResponse
)
from backend.app.services.marketplace_service import MarketplaceService
from backend.app.api.deps import get_current_factory, get_current_user
from backend.app.models.user import Factory, User

router = APIRouter(prefix="/marketplace", tags=["B2B Transactions & Digital Tracking"])

@router.post("/purchase-requests", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_request(
    req_in: PurchaseRequestCreate,
    current_factory: Factory = Depends(get_current_factory),
    db: Session = Depends(get_db)
):
    """Submit a formal B2B purchase and material acquisition request."""
    req = MarketplaceService.create_purchase_request(db, req_in, current_factory)
    return PurchaseRequestResponse.model_validate(req)

@router.patch("/purchase-requests/{request_id}", response_model=PurchaseRequestResponse)
def update_purchase_request(
    request_id: str,
    update_in: PurchaseRequestUpdate,
    current_factory: Factory = Depends(get_current_factory),
    db: Session = Depends(get_db)
):
    """Allow the listing owner to accept, reject or counter a buyer request."""
    req = MarketplaceService.update_purchase_request(db, request_id, update_in, current_factory)
    return PurchaseRequestResponse.model_validate(req)

@router.get("/purchase-requests", response_model=List[PurchaseRequestResponse])
def list_purchase_requests(
    current_factory: Factory = Depends(get_current_factory),
    db: Session = Depends(get_db)
):
    """List purchase requests submitted by or sent to the active facility."""
    requests = MarketplaceService.list_purchase_requests(db, current_factory.id)
    return [PurchaseRequestResponse.model_validate(r) for r in requests]

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    seller_factory_id: str,
    current_factory: Factory = Depends(get_current_factory),
    db: Session = Depends(get_db)
):
    """Execute a circular material order and initialize digital tracking."""
    order = MarketplaceService.create_order(
        db, order_in, seller_factory_id=seller_factory_id, buyer_factory_id=current_factory.id
    )
    return OrderResponse.model_validate(order)

@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    current_factory: Factory = Depends(get_current_factory),
    db: Session = Depends(get_db)
):
    """List orders and shipments for the active facility."""
    orders = MarketplaceService.list_orders(db, current_factory.id)
    return [OrderResponse.model_validate(o) for o in orders]

@router.post("/orders/{order_id}/tracking", response_model=TrackingRecordResponse)
def add_tracking_checkpoint(
    order_id: str,
    update_in: TrackingUpdateCreate,
    current_factory: Factory = Depends(get_current_factory),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Append a shipment event for an order owned by the current facility."""
    order = MarketplaceService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="أمر التوريد غير موجود")
    if current_factory.id not in (order.seller_factory_id, order.buyer_factory_id):
        raise HTTPException(status_code=403, detail="غير مصرح بتحديث هذا الأمر")
    if any(term in update_in.status_update.lower() for term in ("verified", "inspected", "مؤكد", "تم الفحص")) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="حالات التحقق والفحص تتطلب مسؤول النظام بعد مراجعة المستندات")
    update_in.verified_by = current_user.email if current_user.is_superuser else None
    record = MarketplaceService.add_tracking_checkpoint(db, order_id, update_in)
    return TrackingRecordResponse.model_validate(record)
