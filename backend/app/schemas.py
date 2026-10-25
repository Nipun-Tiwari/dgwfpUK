from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    dataLoaded: bool


class MetaResponse(BaseModel):
    ingestedAt: str
    cutoff: str
    units: str
    timezoneNote: str
    sources: list[str]
    deliveryDateRange: dict[str, str]
    forecastPublishRange: dict[str, str]
    generationUnitsNote: str


class MetricsResponse(BaseModel):
    mae: Optional[float]
    rmse: Optional[float]
    bias: Optional[float]
    nmae: Optional[float]
    nrmse: Optional[float]
    normalizedOmitted: bool
    completeness: float
    hoursTotal: int
    hoursComplete: int
    hoursIncomplete: int
    hoursMissingForecast: int
    hoursMissingActual: int
    units: str = "MW"


class TimeseriesPoint(BaseModel):
    deliveryHour: str
    forecast: Optional[float]
    actual: Optional[float]
    error: Optional[float]
    selectedPublishTime: Optional[str]
    complete: bool


class TimeseriesResponse(BaseModel):
    units: str = "MW"
    points: list[TimeseriesPoint]


class ErrorResponse(BaseModel):
    error: str
    message: str
