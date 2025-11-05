from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.api.deps import get_db
from src.schemas.user import User, UserCreate, UserUpdate, Courier
from src.schemas.address import Address, AddressCreate, AddressUpdate
from src.services.user import (
    get_user, create_user, update_user, delete_user, get_user_by_email, get_courier, get_user_addresses
)
from src.services.address import create_user_address, update_user_address, delete_user_address, get_address

router = APIRouter()

@router.get("/profile/{user_id}", response_model=User)
async def get_user_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/profile/{user_id}", response_model=User)
async def update_user_profile(user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    db_user = await update_user(db, user_id, user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/couriers/{courier_id}", response_model=Courier)
async def get_courier_info(courier_id: int, db: AsyncSession = Depends(get_db)):
    db_courier = await get_courier(db, courier_id)
    if db_courier is None:
        raise HTTPException(status_code=404, detail="Courier not found")
    return db_courier

@router.delete("/{user_id}")
async def delete_user_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await delete_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.get("/{user_id}/addresses", response_model=List[Address])
async def get_addresses(user_id: int, db: AsyncSession = Depends(get_db)):
    if not await get_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return await get_user_addresses(db, user_id)

@router.post("/{user_id}/addresses", response_model=Address)
async def create_address(user_id: int, address: AddressCreate, db: AsyncSession = Depends(get_db)):
    existing_list = await get_user_addresses(db, user_id)
    for existing in existing_list:
        if (
            existing.address_line == address.address_line and
            existing.city == address.city and
            existing.state == address.state and
            existing.postal_code == address.postal_code and
            existing.country == address.country
        ):
            await create_user_address(db, user_id, address)
            raise HTTPException(status_code=409, detail="Address already exists for this user")

    db_address = await create_user_address(db, user_id, address)
    if db_address is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_address

@router.put("/{user_id}/addresses/{address_id}", response_model=Address)
async def update_address(
    user_id: int, 
    address_id: int, 
    address_update: AddressUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # Check if user exists
    if not await get_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    db_address = await update_user_address(db, user_id, address_id, address_update)
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    return db_address

@router.delete("/{user_id}/addresses/{address_id}")
async def delete_address(user_id: int, address_id: int, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    if not await get_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    db_address = await delete_user_address(db, user_id, address_id)
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    return {"message": "Address deleted successfully"}

@router.post("/", response_model=User)
async def create_new_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_user(db, user)