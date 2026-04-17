"""Transaction domain models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionChannel(str, Enum):
    CARD_PRESENT = "card_present"
    CARD_NOT_PRESENT = "card_not_present"
    ACH = "ach"
    WIRE = "wire"
    ATM = "atm"
    ONLINE = "online"
    BRANCH = "branch"
    MOBILE = "mobile"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CLEARED = "cleared"
    DECLINED = "declined"
    REVERSED = "reversed"
    FLAGGED = "flagged"


class GeoLocation(BaseModel):
    lat: float
    lon: float


class Transaction(BaseModel):
    """Immutable ledger event — primary fraud detection signal."""

    txn_id: str
    customer_id: str
    account_id: str
    amount: float
    currency: str = "USD"
    merchant: Optional[str] = None
    merchant_category: Optional[str] = None
    channel: TransactionChannel
    device_id: Optional[str] = None
    geo: Optional[GeoLocation] = None
    status: TransactionStatus = TransactionStatus.PENDING
    branch_id: Optional[str] = None
    event_ts: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class DeviceProfile(BaseModel):
    """Device fingerprint linked to transactions."""

    device_id: str
    customer_id: str
    device_type: str  # mobile | browser | pos_terminal
    first_seen: datetime
    last_seen: datetime
    ip_addresses: list[str] = Field(default_factory=list)
    is_trusted: bool = False
