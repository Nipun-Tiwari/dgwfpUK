import math
from dataclasses import dataclass, field

from .matching import MatchedHour

NMAE_MIN_ACTUAL_MW = 100.0


@dataclass
class MetricsResult:
    mae: float | None
    rmse: float | None
    bias: float | None
    nmae: float | None
    nrmse: float | None
    normalizedOmitted: bool
    completeness: float
    hoursTotal: int
    hoursComplete: int
    hoursIncomplete: int
    hoursMissingForecast: int
    hoursMissingActual: int
    units: str = field(default="MW")


def compute_metrics(hours: list[MatchedHour]) -> MetricsResult:
    hours_total = len(hours)
    complete = [h for h in hours if h.complete]
    hours_complete = len(complete)
    hours_incomplete = hours_total - hours_complete
    hours_missing_forecast = sum(1 for h in hours if h.missingForecast)
    hours_missing_actual = sum(1 for h in hours if h.missingActual)

    if hours_total == 0:
        return MetricsResult(
            mae=None, rmse=None, bias=None, nmae=None, nrmse=None,
            normalizedOmitted=True, completeness=0.0,
            hoursTotal=0, hoursComplete=0, hoursIncomplete=0,
            hoursMissingForecast=0, hoursMissingActual=0,
        )

    completeness = hours_complete / hours_total

    if not complete:
        return MetricsResult(
            mae=None, rmse=None, bias=None, nmae=None, nrmse=None,
            normalizedOmitted=True, completeness=completeness,
            hoursTotal=hours_total, hoursComplete=hours_complete,
            hoursIncomplete=hours_incomplete,
            hoursMissingForecast=hours_missing_forecast,
            hoursMissingActual=hours_missing_actual,
        )

    errors = [h.error_mw for h in complete]
    actuals = [h.actual_mw for h in complete]
    n = len(complete)

    mae = sum(abs(e) for e in errors) / n  # type: ignore[arg-type]
    rmse = math.sqrt(sum(e**2 for e in errors) / n)  # type: ignore[operator]
    bias = sum(errors) / n  # type: ignore[arg-type]
    mean_actual = sum(actuals) / n  # type: ignore[arg-type]

    if mean_actual < NMAE_MIN_ACTUAL_MW:
        nmae, nrmse, normalized_omitted = None, None, True
    else:
        nmae = (mae / mean_actual) * 100.0
        nrmse = (rmse / mean_actual) * 100.0
        normalized_omitted = False

    return MetricsResult(
        mae=mae,
        rmse=rmse,
        bias=bias,
        nmae=nmae,
        nrmse=nrmse,
        normalizedOmitted=normalized_omitted,
        completeness=completeness,
        hoursTotal=hours_total,
        hoursComplete=hours_complete,
        hoursIncomplete=hours_incomplete,
        hoursMissingForecast=hours_missing_forecast,
        hoursMissingActual=hours_missing_actual,
    )
