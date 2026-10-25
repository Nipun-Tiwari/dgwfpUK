import logging
from datetime import datetime, timezone

from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger(__name__)


def _parse_utc(v: str) -> datetime:
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class WindforRecord(BaseModel):
    startTime: datetime
    publishTime: datetime
    generation_mw: float | None = None

    @field_validator("startTime", "publishTime", mode="before")
    @classmethod
    def parse_time(cls, v: str) -> datetime:
        try:
            return _parse_utc(v)
        except Exception:
            raise ValueError(f"Unparseable timestamp: {v!r}")

    @model_validator(mode="before")
    @classmethod
    def extract_generation(cls, data: dict) -> dict:
        if "generation_mw" not in data and "generation" in data:
            try:
                gen = data["generation"]
                data["generation_mw"] = float(gen) if gen is not None else None
            except (TypeError, ValueError):
                logger.warning("Malformed generation value: %r", data.get("generation"))
                data["generation_mw"] = None
        return data


class FuelhhRecord(BaseModel):
    startTime: datetime
    settlementDate: str
    settlementPeriod: int
    generation_mw: float | None = None

    @field_validator("startTime", mode="before")
    @classmethod
    def parse_time(cls, v: str) -> datetime:
        try:
            return _parse_utc(v)
        except Exception:
            raise ValueError(f"Unparseable timestamp: {v!r}")

    @model_validator(mode="before")
    @classmethod
    def extract_generation(cls, data: dict) -> dict:
        if "generation_mw" not in data and "generation" in data:
            try:
                gen = data["generation"]
                data["generation_mw"] = float(gen) if gen is not None else None
            except (TypeError, ValueError):
                logger.warning("Malformed generation value: %r", data.get("generation"))
                data["generation_mw"] = None
        return data
