from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import ConfigDict, BaseModel, EmailStr, Field

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    factory: Optional[Dict[str, Any]] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

# Factory Schemas
class FactoryBase(BaseModel):
    name: str
    sector: str = "غير محدد"
    role: str = "Waste Producer"
    city: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    description: Optional[str] = None

class FactoryCreate(FactoryBase):
    pass

class FactoryUpdate(BaseModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    role: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    description: Optional[str] = None

class FactoryResponse(FactoryBase):
    id: str
    owner_id: Optional[str] = None
    sustainability_score: float
    is_verified: bool
    data_origin: str = "user_submitted"
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_date: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
