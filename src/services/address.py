from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.models.address import Address
from src.schemas.address import AddressCreate
from src.services.user import get_user, get_user_addresses

async def create_user_address(db: AsyncSession, user_id: int, address: AddressCreate):
    user = await get_user(db, user_id)
    if not user:
        return None
    
    existing_addresses = await get_user_addresses(db, user_id)

    for existing in existing_addresses:
        if (
            existing.address_line == address.address_line and
            existing.city == address.city and
            existing.state == address.state and
            existing.postal_code == address.postal_code and
            existing.country == address.country
        ):
            if address.is_primary and not existing.is_primary:
                for addr in existing_addresses:
                    if addr.is_primary:
                        addr.is_primary = False
                existing.is_primary = True
                await db.commit()
                await db.refresh(existing)
            return existing

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