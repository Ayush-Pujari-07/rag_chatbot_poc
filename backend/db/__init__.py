from config import settings
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client[settings.PROJECT_NAME]


def get_db():
    return db
