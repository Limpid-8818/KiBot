from typing import Optional

from .client import QWeatherClient
from service.weather.models import WeatherResponse, WarningResponse, StormResponse


class WeatherService:
    def __init__(self):
        self.client = QWeatherClient()

    async def get_now(self, city: str) -> Optional[WeatherResponse]:
        location = await self.client.get_location(city)
        if not location:
            return None
        now = await self.client.get_now_weather(location.id)
        return WeatherResponse(location=location, now=now)

    async def get_today(self, city: str) -> Optional[WeatherResponse]:
        location = await self.client.get_location(city)
        if not location:
            return None
        today_forecast = await self.client.get_today_forecast(location.id)
        if today_forecast is None:
            return None
        return WeatherResponse(
            location=location,
            daily=[today_forecast]
        )

    async def get_warning(self, city: str) -> Optional[WarningResponse]:
        location = await self.client.get_location(city)
        if not location:
            return None
        warnings = await self.client.get_warning_info(location.id)
        if warnings is None:
            return None
        return WarningResponse(
            location=location,
            warningInfo=warnings
        )

    async def get_storm(self) -> Optional[list[StormResponse]]:
        storms = await self.client.get_active_storm_list()
        print(storms)
        resp: list[StormResponse] = []
        if not storms:
            return None
        for storm in storms:
            storm_info = await self.client.get_now_storm_info(storm.id)
            storm_resp_item = StormResponse(
                storm=storm,
                stormInfo=storm_info
            )
            resp.append(storm_resp_item)
        if not resp:
            return None
        return resp
