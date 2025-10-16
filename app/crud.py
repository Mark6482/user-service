from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import User, Address
from app.schemas import UserCreate, UserUpdate, AddressCreate

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
    # Явно загружаем адреса для нового пользователя
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
        # Явно загружаем адреса после обновления
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

async def get_user_addresses(db: AsyncSession, user_id: int):
    result = await db.execute(select(Address).filter(Address.user_id == user_id))
    return result.scalars().all()

async def create_user_address(db: AsyncSession, user_id: int, address: AddressCreate):
    user = await get_user(db, user_id)
    if not user:
        return None
    
    existing_addresses = await get_user_addresses(db, user_id)

    # 1) Check for exact duplicate address for this user; if exists, don't add new
    for existing in existing_addresses:
        if (
            existing.address_line == address.address_line and
            existing.city == address.city and
            existing.state == address.state and
            existing.postal_code == address.postal_code and
            existing.country == address.country
        ):
            # If caller wants it primary, flip primary flags accordingly
            if address.is_primary and not existing.is_primary:
                for addr in existing_addresses:
                    if addr.is_primary:
                        addr.is_primary = False
                existing.is_primary = True
                await db.commit()
                await db.refresh(existing)
            return existing

    # 2) No duplicate -> proceed with creation
    is_primary = not existing_addresses or address.is_primary
    
    if is_primary and existing_addresses:
        for addr in existing_addresses:
            addr.is_primary = False
        await db.commit()
    
    db_address = Address(
        user_id=user_id,
        **address.dict()
    )
    db_address.is_primary = is_primary
    
    db.add(db_address)
    await db.commit()
    await db.refresh(db_address)
    return db_address

async def get_courier(db: AsyncSession, courier_id: int):
    result = await db.execute(
        select(User).options(selectinload(User.addresses)).filter(
            User.id == courier_id, User.role == "courier"
        )
    )
    user = result.scalar_one_or_none()
    return user