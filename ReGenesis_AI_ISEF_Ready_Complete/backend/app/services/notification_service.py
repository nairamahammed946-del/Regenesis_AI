from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from backend.app.models.notification import Notification

class NotificationService:
    @staticmethod
    def create(
        db: Session,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "Info",
        link: Optional[str] = None
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
        db.add(notif)
        db.flush()
        return notif

    @staticmethod
    def list_user_notifications(
        db: Session,
        user_id: str,
        limit: int = 20
    ) -> List[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id).order_by(desc(Notification.created_at)).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def mark_read(db: Session, notification_id: str) -> bool:
        stmt = select(Notification).where(Notification.id == notification_id)
        res = db.execute(stmt)
        n = res.scalars().first()
        if n:
            n.is_read = True
            db.flush()
            return True
        return False
