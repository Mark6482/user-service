from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional, Dict

class AddressBase(BaseModel):
    address_line: str
    city: str
    state: str
    postal_code: str
    country: str = "Russia"
    is_primary: bool = False

class AddressCreate(AddressBase):
    pass

class Address(AddressBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    phone: str
    first_name: str
    last_name: str

class UserCreate(UserBase):
    role: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferences: Optional[Dict] = None

class User(UserBase):
    id: int
    role: str
    preferences: Dict
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    addresses: List[Address] = []

    class Config:
        from_attributes = True

class Courier(User):
    rating: Optional[float] = None
    delivery_stats: Optional[Dict] = None