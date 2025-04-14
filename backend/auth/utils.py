import random
import string
from datetime import datetime, timedelta

from auth.config import auth_config
from auth.schemas import RefreshTokenSettings
from config import settings

ALPHA_NUM = string.ascii_letters + string.digits


def get_refresh_token_settings(
    refresh_token: str,
    expired: bool = False,
) -> RefreshTokenSettings:
    if expired:
        return RefreshTokenSettings(
            key=auth_config.REFRESH_TOKEN_KEY,
            secure=auth_config.SECURE_COOKIES,
            domain=settings.SITE_DOMAIN,
        )

    return RefreshTokenSettings(
        key=auth_config.REFRESH_TOKEN_KEY,
        secure=auth_config.SECURE_COOKIES,
        domain=settings.SITE_DOMAIN,
        value=refresh_token,
        max_age=auth_config.REFRESH_TOKEN_EXP,
    )


def generate_random_alphanum(length: int = 20) -> str:
    return "".join(random.choices(ALPHA_NUM, k=length))


def calculate_refresh_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(seconds=auth_config.REFRESH_TOKEN_EXP)
