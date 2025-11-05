import json
import logging
from aiokafka import AIOKafkaProducer
from src.core.config import settings

logger = logging.getLogger(__name__)

class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_event(self, topic: str, event_data: dict):
        try:
            if self.producer:
                await self.producer.send_and_wait(topic, event_data)
                logger.info(f"Event sent to topic {topic}: {event_data.get('event_type')}")
            else:
                logger.warning("Kafka producer not initialized")
        except Exception as e:
            logger.error(f"Failed to send event to {topic}: {e}")

    async def send_user_event(self, event_type: str, user_data: dict):
        event = {
            "event_type": event_type,
            "service": "user-service",
            "data": user_data,
            "timestamp": user_data.get('updated_at') or user_data.get('created_at')
        }
        await self.send_event("user-events", event)

    async def send_address_event(self, event_type: str, address_data: dict):
        event = {
            "event_type": event_type,
            "service": "user-service",
            "data": address_data,
            "timestamp": address_data.get('created_at')
        }
        await self.send_event("address-events", event)

# Global producer instance
event_producer = KafkaEventProducer()