import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.crud import get_user_by_email, create_user, update_user
from app.schemas import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            'user.events',
            bootstrap_servers=self.bootstrap_servers,
            group_id="user-service",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')) if v else None
        )
        await self.consumer.start()
        await self.consume_events()

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()

    async def consume_events(self):
        try:
            async for msg in self.consumer:
                try:
                    if not msg.value:
                        continue

                    event_data = msg.value
                    event_type = event_data.get('event_type')
                    payload = event_data.get('data') or {}

                    logger.info(f"Received user event: {event_type}")

                    if event_type in ('user.created', 'user.updated'):
                        await self._upsert_user(payload)
                    else:
                        logger.warning(f"Unknown user event type: {event_type}")

                    await self.consumer.commit()

                except Exception as e:
                    logger.error(f"Error processing user event: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"User consumer error: {e}")

    async def _upsert_user(self, user_payload: dict):
        email = user_payload.get('email')
        if not email:
            logger.warning("user event without email; skipping")
            return

        async with AsyncSessionLocal() as db:
            existing = await get_user_by_email(db, email)
            if existing:
                update = UserUpdate(
                    phone=user_payload.get('phone'),
                    first_name=user_payload.get('first_name'),
                    last_name=user_payload.get('last_name'),
                )
                await update_user(db, existing.id, update)
                logger.info(f"Updated user profile for {email}")
            else:
                create = UserCreate(
                    email=email,
                    phone=user_payload.get('phone') or "",
                    first_name=user_payload.get('first_name') or "",
                    last_name=user_payload.get('last_name') or "",
                    role=user_payload.get('role') or "client",
                )
                await create_user(db, create)
                logger.info(f"Created user profile for {email}")


event_consumer = KafkaEventConsumer()


