from pydantic import BaseModel
from datetime import datetime

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