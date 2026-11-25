from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.notification import NotificationResponse
from backend.app.services.notification_service import NotificationService
from backend.app.api.deps import get_current_user
from backend.app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])

@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List real-time alerts regarding matches, purchase inquiries, and order events."""
    notifs = NotificationService.list_user_notifications(db, current_user.id)
    return [NotificationResponse.model_validate(n) for n in notifs]

@router.put("/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    """Acknowledge and mark an individual alert as read."""
    success = NotificationService.mark_read(db, notification_id)
    return {"status": "success", "updated": success}
