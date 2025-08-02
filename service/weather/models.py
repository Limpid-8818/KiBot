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
