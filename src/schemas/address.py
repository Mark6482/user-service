from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AddressBase(BaseModel):
    address_line: str
    city: str
    state: str
    postal_code: str
    country: str = "Russia"
    is_primary: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(BaseModel):
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_primary: Optional[bool] = None

class Address(AddressBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True