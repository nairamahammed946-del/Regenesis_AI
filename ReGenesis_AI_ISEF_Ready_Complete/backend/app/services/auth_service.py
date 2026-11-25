from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status
from backend.app.models.user import User, Factory
from backend.app.schemas.user import UserCreate, UserLogin
from backend.app.core.security import hash_password, verify_password, create_access_token

class AuthService:
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def register(db: Session, user_in: UserCreate) -> User:
        existing = AuthService.get_by_email(db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="البريد الإلكتروني مسجل بالفعل في المنظومة"
            )
        
        user = User(
            email=user_in.email,
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name,
            phone=user_in.phone,
            is_active=True
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def authenticate(db: Session, credentials: UserLogin) -> User:
        user = AuthService.get_by_email(db, credentials.email)
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="بيانات الدخول غير صحيحة"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="هذا الحساب غير نشط"
            )
        return user
