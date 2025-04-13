import re
from typing import Optional
from typing_extensions import Annotated
from pydantic import EmailStr, Field, field_validator, BaseModel, AfterValidator

# Updated regex to include at least one uppercase letter
STRONG_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[\d])(?=.*[!@#$%^&*])[\w!@#$%^&*]{6,128}$"
)


class AuthUser(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @field_validator("password", mode="after")
    @classmethod
    def valid_password(cls, password: str) -> str:
        if not re.match(STRONG_PASSWORD_PATTERN, password):
            raise ValueError(
                "Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special symbol"
            )
        return password


class AccessTokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    email: EmailStr


Password = Annotated[str, AfterValidator(AuthUser.valid_password)]


class RefreshTokenSettings(BaseModel):
    key: str
    httponly: bool = True
    samesite: str = "none"
    secure: bool
    domain: str
    value: Optional[str] = None
    max_age: Optional[int] = None
