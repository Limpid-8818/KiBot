from typing import Optional, List

from pydantic import BaseModel


class Location(BaseModel):
    name: str
    id: str
    country: str
    adm1: str  # 省级
    adm2: str  # 市/县级


class NowWeather(BaseModel):
    temp: str
    feelsLike: str
    text: str
    windDir: str
    windScale: str
    humidity: str
    pressure: str
    vis: str


class DailyForecast(BaseModel):
    fxDate: str
    tempMax: str
    tempMin: str
    textDay: str
    textNight: str
    windDirDay: str
    windScaleDay: str


class WeatherResponse(BaseModel):
    location: Location
    now: Optional[NowWeather] = None
    daily: Optional[List[DailyForecast]] = None
