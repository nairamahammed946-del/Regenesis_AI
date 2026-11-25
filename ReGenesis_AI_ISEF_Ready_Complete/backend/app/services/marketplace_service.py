import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi import HTTPException
from backend.app.models.marketplace import PurchaseRequest, Order, Transaction, WasteTrackingRecord
from backend.app.models.waste import WasteListing
from backend.app.models.user import Factory
from backend.app.schemas.marketplace import PurchaseRequestCreate, OrderCreate, TrackingUpdateCreate
from backend.app.core.config import settings

class MarketplaceService:
    @staticmethod
    def create_purchase_request(
        db: Session,
        req_in: PurchaseRequestCreate,
        buyer_factory: Factory
    ) -> PurchaseRequest:
        stmt = select(WasteListing).where(WasteListing.id == req_in.listing_id)
        res = db.execute(stmt)
        listing = res.scalars().first()
        if not listing:
            raise HTTPException(status_code=404, detail="إعلان المادة غير موجود")
        if settings.ENVIRONMENT.lower() == "production" and (not listing.factory or not listing.factory.is_verified):
            raise HTTPException(status_code=403, detail="لا يمكن التفاوض مع منشأة غير متحققة")
        trade = str(listing.trade_type or "")
        if "عرض" not in trade and "offer" not in trade.lower():
            raise HTTPException(status_code=400, detail="يمكن تقديم طلب شراء على إعلان عرض فقط")
        if listing.factory_id == buyer_factory.id:
            raise HTTPException(status_code=400, detail="لا يمكن للمنشأة تقديم طلب شراء على إعلانها الخاص")
        if req_in.requested_quantity > float(listing.quantity):
            raise HTTPException(status_code=400, detail="الكمية المطلوبة تتجاوز الكمية المعلنة")

        req = PurchaseRequest(
            listing_id=listing.id,
            buyer_factory_id=buyer_factory.id,
            buyer_factory_name=buyer_factory.name,
            requested_quantity=req_in.requested_quantity,
            offered_price=req_in.offered_price,
            message=req_in.message or "نحن مهتمون بشراء وتوريد هذه الخامة لإعادة الاستخدام في خطوط إنتاجنا.",
            status="Pending"
        )
        db.add(req)
        db.flush()
        return req

    @staticmethod
    def list_purchase_requests(
        db: Session,
        factory_id: Optional[str] = None
    ) -> List[PurchaseRequest]:
        stmt = select(PurchaseRequest).join(WasteListing, PurchaseRequest.listing_id == WasteListing.id).order_by(desc(PurchaseRequest.created_at))
        if factory_id:
            stmt = stmt.where((PurchaseRequest.buyer_factory_id == factory_id) | (WasteListing.factory_id == factory_id))
        result = db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def update_purchase_request(
        db: Session, request_id: str, update_in, seller_factory: Factory
    ) -> PurchaseRequest:
        req = db.execute(select(PurchaseRequest).where(PurchaseRequest.id == request_id)).scalars().first()
        if not req:
            raise HTTPException(status_code=404, detail="طلب الشراء غير موجود")
        listing = db.execute(select(WasteListing).where(WasteListing.id == req.listing_id)).scalars().first()
        if not listing or listing.factory_id != seller_factory.id:
            raise HTTPException(status_code=403, detail="فقط منشأة المورد صاحبة الإعلان يمكنها الرد على الطلب")
        if update_in.status not in {"Accepted", "Rejected", "Countered"}:
            raise HTTPException(status_code=422, detail="حالة الطلب غير مسموحة")
        if update_in.status == "Countered" and update_in.counter_price is None:
            raise HTTPException(status_code=422, detail="أدخل السعر المقابل عند التفاوض")
        req.status = update_in.status
        req.counter_price = update_in.counter_price if update_in.status == "Countered" else None
        db.add(req)
        db.flush()
        return req

    @staticmethod
    def create_order(
        db: Session,
        order_in: OrderCreate,
        seller_factory_id: str,
        buyer_factory_id: str
    ) -> Order:
        listing_stmt = select(WasteListing).where(WasteListing.id == order_in.listing_id)
        listing = db.execute(listing_stmt).scalars().first()
        if not listing:
            raise HTTPException(status_code=404, detail="إعلان المادة غير موجود")
        if settings.ENVIRONMENT.lower() == "production" and (not listing.factory or not listing.factory.is_verified):
            raise HTTPException(status_code=403, detail="المنشأة المالكة للإعلان غير متحققة")
        if listing.factory_id != seller_factory_id:
            raise HTTPException(status_code=403, detail="البائع المحدد لا يملك إعلان المادة")
        if seller_factory_id == buyer_factory_id:
            raise HTTPException(status_code=400, detail="لا يمكن إنشاء طلب بين نفس المنشأة")
        if order_in.quantity <= 0 or order_in.quantity > float(listing.quantity):
            raise HTTPException(status_code=400, detail="كمية الطلب غير صالحة أو تتجاوز الكمية المعلنة")
        if order_in.purchase_request_id:
            req = db.execute(select(PurchaseRequest).where(PurchaseRequest.id == order_in.purchase_request_id)).scalars().first()
            if not req or req.listing_id != listing.id or req.buyer_factory_id != buyer_factory_id:
                raise HTTPException(status_code=400, detail="طلب الشراء المرتبط غير صالح")
            if req.status != "Accepted":
                raise HTTPException(status_code=409, detail="يجب قبول طلب الشراء قبل إنشاء أمر توريد")
            if order_in.quantity > float(req.requested_quantity):
                raise HTTPException(status_code=400, detail="الكمية تتجاوز طلب الشراء المقبول")

        order_num = f"REG-ORD-2026-{uuid.uuid4().hex[:6].upper()}"
        tracking_num = f"TRACK-RG-{uuid.uuid4().hex[:8].upper()}"
        total = round(order_in.quantity * order_in.agreed_price, 2)
        order = Order(
            order_number=order_num, purchase_request_id=order_in.purchase_request_id,
            listing_id=order_in.listing_id, seller_factory_id=seller_factory_id,
            buyer_factory_id=buyer_factory_id, quantity=order_in.quantity,
            agreed_price=order_in.agreed_price, total_amount=total,
            status="Pending_Contract_Confirmation", tracking_number=tracking_num,
            carrier_name=order_in.carrier_name or "To be arranged by parties"
        )
        db.add(order)
        db.flush()

        # No payment gateway/escrow integration exists in this MVP. Record an unpaid placeholder only.
        tx = Transaction(
            order_id=order.id, amount=total, currency="UNSPECIFIED",
            transaction_type="Payment_Due", status="Pending",
            payment_method="Not integrated - arrange payment outside platform",
            reference_number=None
        )
        db.add(tx)

        # This is an order-created event, not proof of loading, weighing or dispatch.
        track = WasteTrackingRecord(
            order_id=order.id, checkpoint_name="إنشاء أمر التوريد",
            location="غير محدد", status_update="Order Created - Awaiting Dispatch",
            notes="لم يتم تسجيل وزن أو تحميل أو شحن فعلي. أضف تحديثاً بعد تنفيذ الحدث والتحقق منه.",
            verified_by=None
        )
        db.add(track)

        return order

    @staticmethod
    def get_order(db: Session, order_id: str) -> Optional[Order]:
        return db.execute(select(Order).where(Order.id == order_id)).scalars().first()

    @staticmethod
    def list_orders(db: Session, factory_id: Optional[str] = None) -> List[Order]:
        stmt = select(Order).order_by(desc(Order.created_at))
        if factory_id:
            stmt = stmt.where((Order.seller_factory_id == factory_id) | (Order.buyer_factory_id == factory_id))
        result = db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def add_tracking_checkpoint(
        db: Session,
        order_id: str,
        update_in: TrackingUpdateCreate
    ) -> WasteTrackingRecord:
        record = WasteTrackingRecord(
            order_id=order_id,
            checkpoint_name=update_in.checkpoint_name,
            location=update_in.location,
            status_update=update_in.status_update,
            notes=update_in.notes,
            verified_by=update_in.verified_by
        )
        db.add(record)
        db.flush()
        return record
