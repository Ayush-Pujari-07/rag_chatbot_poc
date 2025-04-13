from backend.auth.exceptions import EmailTaken
from backend.auth.schemas import AuthUser
from backend.auth.service import get_user_by_email


async def valid_user_create(
    user: AuthUser,
) -> AuthUser:
    if await get_user_by_email(user.email):
        raise EmailTaken()

    return user
