from typing import Any, Dict, Optional

from fastapi import HTTPException

from auth.exceptions import InvalidCredentials
from auth.schemas import AuthUser
from auth.security import check_password, hash_password
from auth.utils import calculate_refresh_token_expiry, generate_random_alphanum
from db import get_db
from logger import logger

# Initialize the database connection and logger
db = get_db()


async def create_user(user_data: AuthUser) -> Dict[str, Any]:
    try:
        hashed_password = hash_password(user_data.password)
        created_user = {
            "name": user_data.name,
            "email": user_data.email.lower(),
            "password": hashed_password,
        }

        # Check if user already exists
        existing_user = await get_user_by_email(user_data.email.lower())
        if existing_user:
            logger.warning(f"User already exists: {user_data.email}")
            raise HTTPException(status_code=400, detail="User already exists")

        result = await db["users"].insert_one(created_user)
        created_user["_id"] = result.inserted_id
        return created_user
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e


async def authenticate_user(auth_data: AuthUser) -> Dict[str, Any]:
    try:
        user = await get_user_by_email(auth_data.email.lower())
        if not user or not check_password(auth_data.password, user["password"]):
            logger.warning(f"Invalid credentials for user: {auth_data.email}")
            raise InvalidCredentials()
        logger.info(f"User authenticated: {auth_data.email}")
        return user
    except InvalidCredentials as e:
        raise e
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e


async def create_refresh_token(
    user_id: str, refresh_token: Optional[str] = None
) -> str:
    if not refresh_token:
        refresh_token = generate_random_alphanum(64)

    new_refresh_token = {
        "refresh_token": refresh_token,
        "expires_at": calculate_refresh_token_expiry(),
        "user_id": user_id,
    }
    await db["refresh_tokens"].insert_one(new_refresh_token)
    return refresh_token or new_refresh_token["refresh_token"]


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    return await db["users"].find_one({"email": email.lower()})


async def get_refresh_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    return await db["refresh_tokens"].find_one({"refresh_token": refresh_token})
