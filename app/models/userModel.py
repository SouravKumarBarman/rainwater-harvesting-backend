from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from pydantic.functional_validators import BeforeValidator
from typing import Optional

PyObjectId = Annotated[str, BeforeValidator(str)]


class loginUserModel(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)


class registerUserModel(loginUserModel):
    username: str = Field(...)


class userOut(BaseModel):
    # user field to be returned to client
    id: PyObjectId = Field(alias="_id")
    email: EmailStr = Field(...)
    username: str = Field(...)
    model_config = ConfigDict(populate_by_name=True)


class UserInDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str = Field(...)
    email: EmailStr = Field(...)
    hashed_password: str = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    refresh_token: Optional[str] = Field(default=None)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
