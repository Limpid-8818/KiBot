from datetime import date
from typing import Optional, Union, List, Tuple

from pydantic import BaseModel


class DateMeta(BaseModel):
    date: date  # 日期
    lunar_date: Optional[str] = None  # 农历日期
    is_workday: bool = True   # 是否工作日
    is_weekend: bool = False  # 是否周末
    is_holiday: bool = False   # 是否法定节假日(即是否是休息日)
    holiday_name: Optional[Union[str, List[str]]] = None  # 节日的名称，可为复数
    yesterday: Optional["DateMeta"] = None
    tomorrow: Optional["DateMeta"] = None
    special: Optional[List[str]] = None   # 关于这个日期的一些附加信息


class Festival(BaseModel):
    name: str
    name_zh: str
    month: int
    day: Optional[int] = None   # 固定日
    nth_weekday: Optional[Tuple[int, int]] = None   # 第几周, 星期几
