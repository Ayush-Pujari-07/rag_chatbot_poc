import os
from motor.motor_asyncio import AsyncIOMotorClient


def get_db(db_name: str):
    MONGO_URI = os.environ.get("MONGODB_URI")
    if not MONGO_URI:
        raise ValueError("MONGODB_URI environment variable is not set")

    client = AsyncIOMotorClient(MONGO_URI)
    return client[db_name]
