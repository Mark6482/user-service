from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
from typing import List

from app.database import get_db, engine, Base
from app.schemas import User, UserCreate, UserUpdate, Address, AddressCreate, Courier
from app.crud import (
    get_user, create_user, update_user, delete_user,
    get_user_addresses, create_user_address, get_courier, get_user_by_email
)

import logging
logger = logging.getLogger(__name__)

app = FastAPI(title="User Service", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start Kafka consumer for user events
    from app.kafka.consumer import event_consumer
    import asyncio
    asyncio.create_task(event_consumer.start())

@app.on_event("shutdown")
async def shutdown_event():
    from app.kafka.consumer import event_consumer
    await event_consumer.stop()

@app.get("/users/profile/{user_id}", response_model=User)
async def get_user_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/profile/{user_id}", response_model=User)
async def update_user_profile(user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    db_user = await update_user(db, user_id, user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/users/couriers/{courier_id}", response_model=Courier)
async def get_courier_info(courier_id: int, db: AsyncSession = Depends(get_db)):
    db_courier = await get_courier(db, courier_id)
    if db_courier is None:
        raise HTTPException(status_code=404, detail="Courier not found")
    return db_courier

@app.delete("/users/{user_id}")
async def delete_user_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await delete_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@app.get("/users/{user_id}/addresses", response_model=List[Address])
async def get_addresses(user_id: int, db: AsyncSession = Depends(get_db)):
    if not await get_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return await get_user_addresses(db, user_id)

@app.post("/users/{user_id}/addresses", response_model=Address)
async def create_address(user_id: int, address: AddressCreate, db: AsyncSession = Depends(get_db)):
    # Pre-check for exact duplicate to return proper status code
    existing_list = await get_user_addresses(db, user_id)
    for existing in existing_list:
        if (
            existing.address_line == address.address_line and
            existing.city == address.city and
            existing.state == address.state and
            existing.postal_code == address.postal_code and
            existing.country == address.country
        ):
            # still apply primary toggle if requested
            await create_user_address(db, user_id, address)
            raise HTTPException(status_code=409, detail="Address already exists for this user")

    db_address = await create_user_address(db, user_id, address)
    if db_address is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_address

@app.post("/users/", response_model=User)
async def create_new_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_user(db, user)

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "user-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)