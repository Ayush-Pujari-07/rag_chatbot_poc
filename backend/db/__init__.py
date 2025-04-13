from motor.motor_asyncio import AsyncIOMotorClient

from backend.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client[settings.PROJECT_NAME]


def get_db():
    return db
