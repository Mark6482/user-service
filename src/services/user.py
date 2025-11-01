from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.db.models.user import User
from src.db.models.address import Address
from src.schemas.user import UserCreate, UserUpdate

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(User).options(selectinload(User.addresses)).filter(User.id == user_id)
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(User).options(selectinload(User.addresses)).filter(User.email == email)
    )
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: UserCreate):
    db_user = User(
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    result = await db.execute(
        select(User).options(selectinload(User.addresses)).filter(User.id == db_user.id)
    )
    return result.scalar_one_or_none()

async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate):
    db_user = await get_user(db, user_id)
    if db_user:
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        await db.commit()
        await db.refresh(db_user)
        result = await db.execute(
            select(User).options(selectinload(User.addresses)).filter(User.id == user_id)
        )
        return result.scalar_one_or_none()
    return None

async def delete_user(db: AsyncSession, user_id: int):
    db_user = await get_user(db, user_id)
    if db_user:
        await db.delete(db_user)
        await db.commit()
    return db_user

async def get_courier(db: AsyncSession, courier_id: int):
    result = await db.execute(
        select(User).options(selectinload(User.addresses)).filter(
            User.id == courier_id, User.role == "courier"
        )
    )
    user = result.scalar_one_or_none()
    return user

async def get_user_addresses(db: AsyncSession, user_id: int):
    result = await db.execute(select(Address).filter(Address.user_id == user_id))
    return result.scalars().all()