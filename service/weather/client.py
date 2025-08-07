from datetime import datetime
from typing import Optional

import httpx

from infra.config.settings import settings
from infra.logger import logger
from .models import Location, NowWeather, DailyForecast, WarningInfo, StormItem, StormInfo


class QWeatherClient:

    def __init__(self):
        self.api_host = settings.WEATHER_API_HOST
        self.api_key = settings.WEATHER_API_KEY
        self.client = httpx.AsyncClient(
            headers={"X-QW-Api-Key": self.api_key},
            timeout=httpx.Timeout(10, connect=5),
        )

    async def get_location(self, city: str) -> Optional[Location]:
        url = f"https://{self.api_host}/geo/v2/city/lookup"
        params = {"location": city}

        try:
            resp = await self.client.get(url, params=params)
        except httpx.TimeoutException:
            logger.warn("Weather", f"[{city}] Get Loc Timeout")
            return None

        if resp.status_code != 200:
            print(f"[ERROR] HTTP {resp.status_code}, body: {resp.text}")
            return None

        try:
            data = resp.json()
        except Exception as e:
            print(f"[ERROR] JSON 解析失败: {e}, body: {resp.text[:200]}")
            return None

        if data.get("code") == "200" and data.get("location"):
            loc = data["location"][0]
            return Location(
                name=loc["name"],
                id=loc["id"],
                country=loc["country"],
                adm1=loc["adm1"],
                adm2=loc["adm2"]
            )
        return None

    async def get_now_weather(self, location_id: str) -> Optional[NowWeather]:
        url = f"https://{self.api_host}/v7/weather/now"
        params = {"location": location_id}
        try:
            resp = await self.client.get(url, params=params)
        except httpx.TimeoutException:
            logger.warn("Weather", f"[{location_id}] Get Now Weather Timeout")
            return None
        data = resp.json()
        if data.get("code") == "200":
            now = data["now"]
            return NowWeather(**now)
        return None

    async def get_daily_forecast(self, location_id: str) -> Optional[list[DailyForecast]]:
        url = f"https://{self.api_host}/v7/weather/7d"
        params = {"location": location_id}
        try:
            resp = await self.client.get(url, params=params)
        except httpx.TimeoutException:
            logger.warn("Weather", f"[{location_id}] Get Forecast Weather Timeout")
            return None
        data = resp.json()
        if data.get("code") == "200":
            return [DailyForecast(**item) for item in data["daily"]]
        return None

    async def get_today_forecast(self, location_id: str) -> Optional[DailyForecast]:
        daily_list = await self.get_daily_forecast(location_id)
        if daily_list:
            return daily_list[0]
        return None

    async def get_warning_info(self, location_id: str) -> Optional[list[WarningInfo]]:
        url = f"https://{self.api_host}/v7/warning/now"
        params = {"location": location_id}
        try:
            resp = await self.client.get(url, params=params)
        except httpx.TimeoutException:
            logger.warn("Weather", f"[{location_id}] Get Warning Timeout")
            return None
        data = resp.json()
        if data.get("code") == "200":
            return [WarningInfo(**warning) for warning in data["warning"]]
        return None

    async def get_storm_list(self) -> Optional[list[StormItem]]:
        url = f"https://{self.api_host}/v7/tropical/storm-list"
        year = str(datetime.now().year)
        params = {"basin": "NP", "year": year}
        try:
            resp = await self.client.get(url, params=params)
        except httpx.TimeoutException:
            logger.warn("Weather", f"[{year}] Get Storm List Timeout")
            return None
        data = resp.json()
        if data.get("code") == "200":
            return [StormItem(**storm) for storm in data["storm"]]
        return None

    async def get_active_storm_list(self) -> Optional[list[StormItem]]:
        storms = await self.get_storm_list()
        active = [s for s in storms if s.isActive == "1"]
        return active if active else None

    async def get_now_storm_info(self, storm_id: str) -> Optional[StormInfo]:
        url = f"https://{self.api_host}/v7/tropical/storm-track"
        params = {"stormid": storm_id}
        try:
            resp = await self.client.get(url, params=params)
        except httpx.TimeoutException:
            logger.warn("Weather", f"Storm Id [{storm_id}] Get Storm Info Timeout")
            return None
        data = resp.json()
        if data.get("code") == "200" and data.get("now"):
            storm_now = data["now"]
            return StormInfo(**storm_now)
        return None
