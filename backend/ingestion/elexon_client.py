import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
MAX_RETRIES = 5


async def fetch_json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> Any:
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(url, params=params, timeout=30.0)
            if resp.status_code == 429:
                logger.warning("Rate limited (429), retry %d, waiting %.1fs", attempt + 1, delay)
                await asyncio.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.error("Timeout fetching %s params=%s", url, params)
            raise
        except httpx.HTTPStatusError as e:
            if attempt < MAX_RETRIES - 1 and e.response.status_code >= 500:
                logger.warning("HTTP %d, retry %d", e.response.status_code, attempt + 1)
                await asyncio.sleep(delay)
                delay *= 2
                continue
            logger.error("HTTP error %d fetching %s", e.response.status_code, url)
            raise
    raise RuntimeError(f"Max retries exceeded for {url}")


async def fetch_windfor(
    client: httpx.AsyncClient,
    base_url: str,
    publish_from: datetime,
    publish_to: datetime,
    page_size: int = 5000,
) -> list[dict[str, Any]]:
    params = {
        "publishDateTimeFrom": publish_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "publishDateTimeTo": publish_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pageSize": page_size,
        "format": "json",
    }
    data = await fetch_json(client, f"{base_url}/datasets/WINDFOR", params)
    return data.get("data", data) if isinstance(data, dict) else data


async def fetch_fuelhh(
    client: httpx.AsyncClient,
    base_url: str,
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    params = {
        "settlementDateFrom": date_from,
        "settlementDateTo": date_to,
        "fuelType": "WIND",
        "format": "json",
    }
    data = await fetch_json(client, f"{base_url}/datasets/FUELHH", params)
    return data.get("data", data) if isinstance(data, dict) else data
