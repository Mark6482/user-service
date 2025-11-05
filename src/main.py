from fastapi import FastAPI
import uvicorn
import logging

from src.core.config import settings
from src.db.session import engine, Base
from src.api.v1.api import api_router
from src.utils.kafka.consumer import event_consumer
from src.utils.kafka.producer import event_producer
import asyncio

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await event_producer.start()
    asyncio.create_task(event_consumer.start())

@app.on_event("shutdown")
async def shutdown_event():
    await event_consumer.stop()
    await event_producer.stop()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)