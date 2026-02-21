from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountBase(BaseModel):
    name: str
    region: str = "eu"
    realm: str | None = None
    is_default: bool = False


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = None
    realm: str | None = None
    is_default: bool | None = None


class AccountOut(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    blizzard_battletag: str | None = None
    created_at: datetime
    updated_at: datetime
