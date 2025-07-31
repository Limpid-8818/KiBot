from typing import Optional

from client import QWeatherClient
from service.weather.models import WeatherResponse


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
