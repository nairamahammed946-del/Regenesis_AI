from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from backend.app.services.auth_service import AuthService
from backend.app.services.factory_service import FactoryService
from backend.app.schemas.user import FactoryCreate
from backend.app.core.security import create_access_token
from backend.app.api.deps import get_current_user
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication & Factory Profiles"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    factory_name: str = "منشأة صناعية جديدة",
    role: str = "غير محدد",
    sector: str = "غير محدد",
    city: str = "غير محدد",
    db: Session = Depends(get_db)
):
    """Register a new factory representative user and assign an enterprise profile."""
    user = AuthService.register(db, user_in)
    
    # Auto-provision an unverified facility profile; never auto-claim an existing directory record.
    if FactoryService.get_by_name(db, factory_name):
        raise HTTPException(status_code=409, detail="اسم المنشأة مسجل بالفعل. تواصل مع الدعم لطلب ربط الحساب بالسجل الحالي.")
    FactoryService.create(
        db,
        FactoryCreate(
            name=factory_name,
            sector=sector,
            role=role,
            city=city,
            contact_email=user.email,
            contact_phone=user.phone
        ),
        owner_id=user.id
    )

    token = create_access_token(user.id)
    factory = FactoryService.get_by_user_id(db, user.id)
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user), factory={"id": factory.id, "name": factory.name, "sector": factory.sector, "role": factory.role, "city": factory.city, "is_verified": factory.is_verified} if factory else None)

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate factory user via email & password and return a JWT access token."""
    user = AuthService.authenticate(db, credentials)
    token = create_access_token(user.id)
    factory = FactoryService.get_by_user_id(db, user.id)
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user), factory={"id": factory.id, "name": factory.name, "sector": factory.sector, "role": factory.role, "city": factory.city, "is_verified": factory.is_verified} if factory else None)

@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get authenticated user profile."""
    return UserResponse.model_validate(current_user)
