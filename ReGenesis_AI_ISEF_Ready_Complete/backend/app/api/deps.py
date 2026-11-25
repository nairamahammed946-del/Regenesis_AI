from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token, oauth2_scheme
from backend.app.models.user import User, Factory
from backend.app.services.auth_service import AuthService
from backend.app.services.factory_service import FactoryService

def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    return AuthService.get_by_id(db, user_id)

def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="يرجى تسجيل الدخول للوصول إلى هذا الإجراء",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

def get_current_factory(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Factory:
    factory = FactoryService.get_by_user_id(db, user.id)
    if not factory:
        from backend.app.schemas.user import FactoryCreate
        factory = FactoryService.create(
            db,
            FactoryCreate(
                name=f"مصنع {user.full_name}",
                city="غير محدد",
                contact_email=user.email,
                contact_phone=user.phone
            ),
            owner_id=user.id
        )
    return factory
