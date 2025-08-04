from typing import Optional, List, Literal

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


class WarningInfo(BaseModel):
    id: str  # 预警唯一标识
    sender: str  # 预警消息源
    pubTime: str
    title: str
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    status: str  # 发布状态
    severity: str  # 预警等级
    severityColor: str
    type: str
    typeName: str
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    text: str  # 预警文本描述
    related: Optional[str] = None


class WarningResponse(BaseModel):
    location: Location
    warningInfo: Optional[List[WarningInfo]] = None


class StormItem(BaseModel):
    id: str
    name: str
    basin: str  # 所属区域, NP=西北太平洋
    year: int
    isActive: Literal["0", "1"]


class StormInfo(BaseModel):
    pubTime: str
    lat: str
    lon: str
    type: Literal["TD", "TS", "STS", "TY", "STY", "SuperTY"]
    pressure: str
    windSpeed: str
    moveSpeed: str
    moveDir: Literal["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    move360: str


class StormResponse(BaseModel):
    storm: StormItem
    stormInfo: StormInfo
