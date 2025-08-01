from typing import List, Optional, Dict
from pydantic import BaseModel


class Weekday(BaseModel):
    en: str
    cn: str
    ja: str
    id: int


class SubjectImage(BaseModel):
    large: str
    common: str
    medium: str
    small: str
    grid: str


class SubjectRating(BaseModel):
    total: int
    count: Dict[str, int]
    score: float


class Subject(BaseModel):
    id: int
    url: str
    type: int  # 2 = anime
    name: str
    name_cn: str
    summary: str
    air_date: str
    air_weekday: int
    images: SubjectImage
    rating: SubjectRating
    rank: int


class CalendarDay(BaseModel):
    weekday: Weekday
    items: List[Subject]


class CalendarResponse(BaseModel):
    calendar: List[CalendarDay] 