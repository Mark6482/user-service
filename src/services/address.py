from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from src.db.models.address import Address
from src.schemas.address import AddressCreate, AddressUpdate
from src.services.user import get_user, get_user_addresses
from src.utils.kafka.producer import event_producer
import logging

logger = logging.getLogger(__name__)

def address_to_dict(address: Address) -> dict:
    """Convert Address model to dictionary for event payload"""
    return {
        "id": address.id,
        "user_id": address.user_id,
        "address_line": address.address_line,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "country": address.country,
        "is_primary": address.is_primary,
        "created_at": address.created_at.isoformat() if address.created_at else None
    }

async def get_address(db: AsyncSession, address_id: int, user_id: int = None):
    """Get specific address by ID, optionally filtered by user_id"""
    query = select(Address).filter(Address.id == address_id)
    if user_id:
        query = query.filter(Address.user_id == user_id)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()

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
                
                # Send address.updated event for primary address change
                address_data = address_to_dict(existing)
                await event_producer.send_address_event("address.updated", address_data)
                
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
    
    # Send address.created event
    address_data = address_to_dict(db_address)
    await event_producer.send_address_event("address.created", address_data)
    
    return db_address

async def update_user_address(db: AsyncSession, user_id: int, address_id: int, address_update: AddressUpdate):
    """Update user address"""
    db_address = await get_address(db, address_id, user_id)
    if not db_address:
        return None

    update_data = address_update.dict(exclude_unset=True)
    
    # Handle primary address change
    if update_data.get('is_primary') and not db_address.is_primary:
        # Set all other addresses to non-primary
        user_addresses = await get_user_addresses(db, user_id)
        for addr in user_addresses:
            if addr.id != address_id and addr.is_primary:
                addr.is_primary = False
                await db.commit()
                break
    
    # Update address fields
    for field, value in update_data.items():
        setattr(db_address, field, value)
    
    await db.commit()
    await db.refresh(db_address)
    
    # Send address.updated event
    address_data = address_to_dict(db_address)
    await event_producer.send_address_event("address.updated", address_data)
    
    return db_address

async def delete_user_address(db: AsyncSession, user_id: int, address_id: int):
    """Delete user address"""
    db_address = await get_address(db, address_id, user_id)
    if not db_address:
        return None

    was_primary = db_address.is_primary
    
    await db.delete(db_address)
    await db.commit()
    
    # If deleted address was primary, set another address as primary if available
    if was_primary:
        user_addresses = await get_user_addresses(db, user_id)
        if user_addresses:
            # Set the first address as primary
            user_addresses[0].is_primary = True
            await db.commit()
            
            # Send event for the new primary address
            address_data = address_to_dict(user_addresses[0])
            await event_producer.send_address_event("address.updated", address_data)
    
    # Send address.deleted event
    address_data = address_to_dict(db_address)
    await event_producer.send_address_event("address.deleted", address_data)
    
    return db_address