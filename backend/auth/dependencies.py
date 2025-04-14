from datetime import datetime, timezone
from typing import Any

from fastapi import Cookie

from auth.exceptions import EmailTaken, RefreshTokenNotValid
from auth.schemas import AuthUser, ValidateRefreshTokenResponse
from auth.service import get_refresh_token, get_user_by_email


async def valid_user_create(
    user: AuthUser,
) -> AuthUser:
    if await get_user_by_email(user.email):
        raise EmailTaken()

    return user


async def valid_refresh_token(
    refresh_token: str = Cookie(..., alias="refreshToken"),
) -> ValidateRefreshTokenResponse:
    db_refresh_token = await get_refresh_token(refresh_token)

    if not db_refresh_token:
        raise RefreshTokenNotValid()

    if not _is_valid_refresh_token(db_refresh_token):
        raise RefreshTokenNotValid()

    return ValidateRefreshTokenResponse(
        _id=str(db_refresh_token["_id"]),
        user_id=str(db_refresh_token["user_id"]),
    )


def _is_valid_refresh_token(db_refresh_token: dict[str, Any]) -> bool:
    expires_at = datetime.fromisoformat(str(db_refresh_token["expires_at"])).astimezone(
        timezone.utc
    )
    return datetime.now(timezone.utc) <= expires_at
