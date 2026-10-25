import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.analytics import compute_metrics
from backend.app.matching import MatchedHour

UTC = timezone.utc
FIXTURES = Path(__file__).parent / "fixtures"


def make_hour(delivery_hour_str: str, forecast_mw, actual_mw, complete: bool) -> MatchedHour:
    dh = datetime.fromisoformat(delivery_hour_str.replace("Z", "+00:00"))
    pub = datetime(2025, 12, 31, 7, 30, tzinfo=UTC) if complete else None
    error = (
        (forecast_mw - actual_mw)
        if complete and forecast_mw is not None and actual_mw is not None
        else None
    )
    return MatchedHour(
        deliveryHour=dh,
        forecast_mw=forecast_mw,
        actual_mw=actual_mw,
        error_mw=error,
        selectedPublishTime=pub,
        complete=complete,
        missingForecast=not complete,
        missingActual=not complete,
    )


def test_golden_fixture():
    with open(FIXTURES / "golden_metrics.json") as f:
        golden = json.load(f)

    hours = [
        make_hour(h["deliveryHour"], h["forecast_mw"], h["actual_mw"], h["complete"])
        for h in golden["hours"]
    ]
    result = compute_metrics(hours)
    exp = golden["expected"]

    assert abs(result.mae - exp["mae"]) < 1e-6
    assert abs(result.rmse - exp["rmse"]) < 1e-4
    assert abs(result.bias - exp["bias"]) < 1e-6
    assert result.hoursTotal == exp["hoursTotal"]
    assert result.hoursComplete == exp["hoursComplete"]
    assert result.hoursIncomplete == exp["hoursIncomplete"]
    assert abs(result.completeness - exp["completeness"]) < 1e-9


def test_nmae_nrmse_correct():
    with open(FIXTURES / "golden_metrics.json") as f:
        golden = json.load(f)
    hours = [
        make_hour(h["deliveryHour"], h["forecast_mw"], h["actual_mw"], h["complete"])
        for h in golden["hours"]
    ]
    result = compute_metrics(hours)
    exp = golden["expected"]
    assert result.nmae is not None
    assert result.nrmse is not None
    assert abs(result.nmae - exp["nmae"]) < 1e-4
    assert abs(result.nrmse - exp["nrmse"]) < 1e-4


def test_normalized_omitted_when_mean_actual_low():
    hours = [
        MatchedHour(
            deliveryHour=datetime(2026, 1, 1, 0, tzinfo=UTC),
            forecast_mw=50.0,
            actual_mw=40.0,
            error_mw=10.0,
            selectedPublishTime=datetime(2025, 12, 31, 7, 30, tzinfo=UTC),
            complete=True,
            missingForecast=False,
            missingActual=False,
        )
    ]
    result = compute_metrics(hours)
    assert result.normalizedOmitted
    assert result.nmae is None
    assert result.nrmse is None


def test_empty_input():
    result = compute_metrics([])
    assert result.hoursTotal == 0
    assert result.hoursComplete == 0
    assert result.mae is None
    assert result.normalizedOmitted


def test_incomplete_hours_excluded():
    hours = [
        MatchedHour(
            deliveryHour=datetime(2026, 1, 1, 0, tzinfo=UTC),
            forecast_mw=None, actual_mw=None, error_mw=None, selectedPublishTime=None,
            complete=False, missingForecast=True, missingActual=True,
        ),
        MatchedHour(
            deliveryHour=datetime(2026, 1, 1, 1, tzinfo=UTC),
            forecast_mw=14000.0, actual_mw=15000.0, error_mw=-1000.0,
            selectedPublishTime=datetime(2025, 12, 31, 7, 30, tzinfo=UTC),
            complete=True, missingForecast=False, missingActual=False,
        ),
    ]
    result = compute_metrics(hours)
    assert result.hoursComplete == 1
    assert result.hoursIncomplete == 1
    assert result.mae == 1000.0
