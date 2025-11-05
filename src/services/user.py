from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.db.models.user import User
from src.db.models.address import Address
from src.schemas.user import UserCreate, UserUpdate
from src.utils.kafka.producer import event_producer
import logging

logger = logging.getLogger(__name__)

def user_to_dict(user: User) -> dict:
    """Convert User model to dictionary for event payload"""
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "preferences": user.preferences or {}
    }

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
    
    logger.info(f"User created successfully: {db_user.id}, {db_user.email}")
    
    # Send user.created event (non-blocking)
    try:
        user_data = user_to_dict(db_user)
        logger.info(f"Preparing to send user.created event for user {db_user.id}")
        success = await event_producer.send_user_event("user.created", user_data)
        if success:
            logger.info(f"Successfully sent user.created event for user {db_user.id}")
        else:
            logger.error(f"Failed to send user.created event for user {db_user.id}")
    except Exception as e:
        logger.error(f"Error sending user.created event for user {db_user.id}: {e}")
        # Continue without failing the request
    
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
        
        # Send user.updated event
        try:
            user_data = user_to_dict(db_user)
            await event_producer.send_user_event("user.updated", user_data)
        except Exception as e:
            logger.error(f"Error sending user.updated event: {e}")
        
        result = await db.execute(
            select(User).options(selectinload(User.addresses)).filter(User.id == user_id)
        )
        return result.scalar_one_or_none()
    return None

async def delete_user(db: AsyncSession, user_id: int):
    db_user = await get_user(db, user_id)
    if db_user:
        # Send user.deleted event before actual deletion
        try:
            user_data = user_to_dict(db_user)
            await event_producer.send_user_event("user.deleted", user_data)
        except Exception as e:
            logger.error(f"Error sending user.deleted event: {e}")
        
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