from jose import jwt

from backend.auth.config import auth_config


def create_access_token(
    *,
    user: dict,
) -> str:
    jwt_data = {
        "email": str(user["email"]),
        "password": str(user["password"]),
    }

    # Ensure SECRET_KEY and JWT_ALGORITHM are valid
    if not auth_config.SECRET_KEY:
        raise ValueError("SECRET_KEY is not set in auth_config.")
    if not auth_config.JWT_ALGORITHM:
        raise ValueError("JWT_ALGORITHM is not set in auth_config.")

    return jwt.encode(
        jwt_data,
        auth_config.SECRET_KEY or "",
        auth_config.JWT_ALGORITHM or "",
    )
