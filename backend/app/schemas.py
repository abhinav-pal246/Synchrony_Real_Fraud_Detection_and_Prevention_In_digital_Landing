"""Pydantic models — input validation for every request (Security layer)."""

from typing import Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TransactionIn(BaseModel):
    """Validated fraud-scoring input. Extra fields are allowed but validated where present."""
    model_config = {"extra": "allow"}

    transaction_id: Optional[str] = None
    account_id: Optional[str] = None
    amount: float = Field(ge=0)
    event_time: Optional[str] = None
    mcc: Optional[str] = None
    channel: Optional[str] = None
    entry_method: Optional[str] = None
    card_present: Optional[bool] = None
    cvv_result: Optional[str] = None
    avs_result: Optional[str] = None
    status: Optional[str] = None
    promo_financing: Optional[bool] = None
    gift_card_amount: Optional[float] = Field(default=0, ge=0)
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
