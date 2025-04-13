import logging
import traceback
from fastapi import APIRouter, Depends, Response, status, HTTPException


from backend.auth.jwt import create_access_token
from backend.auth.service import create_user, authenticate_user, create_refresh_token
from backend.auth.utils import get_refresh_token_settings
from backend.auth.dependencies import valid_user_create
from backend.auth.schemas import AccessTokenResponse, AuthUser, UserResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register_user(
    auth_data: AuthUser = Depends(valid_user_create),
) -> UserResponse:
    try:
        user = await create_user(auth_data)
        return UserResponse(email=user["email"])
    except Exception:
        logger.error(
            f"Error creating user with username {auth_data.name}: {traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating user: {traceback.format_exc()}",
        )


@router.post("/users/login", response_model=AccessTokenResponse)
async def auth_user(
    auth_data: AuthUser,
    response: Response,
) -> AccessTokenResponse:
    user = await authenticate_user(auth_data)
    refresh_token_value = await create_refresh_token(user_id=user["_id"])

    response.set_cookie(**get_refresh_token_settings(refresh_token_value).dict())

    return AccessTokenResponse(
        access_token=create_access_token(user=user),
        refresh_token=refresh_token_value,
    )
