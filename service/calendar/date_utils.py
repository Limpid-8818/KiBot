from datetime import date as dt, datetime, time, timedelta
from typing import Tuple

from chinese_calendar import is_workday, is_holiday, get_holiday_detail, get_solar_terms
from zhdate import ZhDate

from .models import Festival, DateMeta

FESTIVALS = (
    Festival(name="Valentine", name_zh="情人节", month=2, day=14),
    Festival(name="White Day", name_zh="白色情人节", month=3, day=14),
    Festival(name="Christmas Eve", name_zh="平安夜", month=12, day=24),
    Festival(name="Christmas", name_zh="圣诞节", month=12, day=25),
    Festival(name="April Fool's Day", name_zh="愚人节", month=4, day=1),
    Festival(name="Halloween", name_zh="万圣节", month=10, day=31),
    Festival(name="Mother's Day", name_zh="母情节", month=5, nth_weekday=(2, 6)),
    Festival(name="Father's day", name_zh="父亲节", month=6, nth_weekday=(3, 6)),
    Festival(name="Thanksgiving", name_zh="感恩节", month=11, nth_weekday=(4, 3)),
)  # 原本想用专门的西方节日类来管理，但似乎不是很方便，弃用

# ------------------ 节日规则表 ------------------
# 固定月日：key=(月, 日), value="中文名"
FIXED_SOLAR: dict[Tuple[int, int], str] = {
    (1, 1): "元旦",
    (2, 14): "情人节",
    (3, 14): "白色情人节",
    (4, 1): "愚人节",
    (5, 1): "劳动节",
    (6, 1): "儿童节",
    # (7, 1): "建党节",
    # (8, 1): "建军节",    # 别给我Bot爆了，就不考虑这俩日子了
    (10, 1): "国庆节",
    (10, 31): "万圣节",
    (12, 24): "平安夜",
    (12, 25): "圣诞节",
}

# 固定月日（农历）→ 中文名
FIXED_LUNAR: dict[Tuple[int, int], str] = {
    (1, 1): "春节",
    (1, 15): "元宵节",
    (5, 5): "端午节",
    (7, 7): "七夕节",
    (8, 15): "中秋节",
    (9, 9): "重阳节",
    (12, 8): "腊八节",
}

# 第 n 周星期 w：((月, 第几周, 星期), 中文名)
WEEKDAY_OFFSET: dict[Tuple[int, int, int], str] = {
    (5, 2, 6): "母亲节",  # 5 月第 2 个星期日
    (6, 3, 6): "父亲节",  # 6 月第 3 个星期日
    (11, 4, 3): "感恩节",  # 11 月第 4 个星期四
}

# 二十四节气表
SOLAR_TERMS_CN = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
    "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
    "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"
]  # 弃用，不如调库来得方便

HOLIDAY_NAME_MAP = {
    "New Year's Day": "元旦",
    "Spring Festival": "春节",
    "Tomb-sweeping Day": "清明",
    "Labour Day": "劳动节",
    "Dragon Boat Festival": "端午",
    "National Day": "国庆节",
    "Mid-autumn Festival": "中秋",
    "Anti-Fascist 70th Day": "中国人民抗日战争暨世界反法西斯战争胜利70周年纪念日",
}


def is_weekend(date: dt) -> bool:
    return date.weekday() >= 5


def nth_weekday(year: int, month: int, n: int, weekday: int) -> int:
    first = dt(year, month, 1)
    days_ahead = (weekday - first.weekday()) % 7
    return 1 + days_ahead + (n - 1) * 7


def check_lieu_day(date_meta: DateMeta) -> bool:
    if date_meta.is_weekend and date_meta.is_workday:
        return True


def add_holiday(date_meta: DateMeta, holiday: str):
    if date_meta.holiday_name is None:
        date_meta.holiday_name = holiday
    elif type(date_meta.holiday_name) is str:
        holiday_name = [date_meta.holiday_name, holiday]
        date_meta.holiday_name = holiday_name
    else:
        date_meta.holiday_name.append(holiday)


def add_special_info(date_meta: DateMeta, special_info: str):
    if date_meta.special is None:
        special_info = [special_info]
        date_meta.special = special_info
    else:
        date_meta.special.append(special_info)


def add_date_info(date_meta: DateMeta):
    # 常规信息
    date_meta.is_workday = is_workday(date_meta.date)
    date_meta.is_weekend = is_weekend(date_meta.date)
    date_meta.is_holiday = is_holiday(date_meta.date)

    # 获取日期信息，随后将节日信息统一写入
    y, m, d = date_meta.date.year, date_meta.date.month, date_meta.date.day
    lunar = ZhDate.from_datetime(datetime.combine(date_meta.date, time.min))
    date_meta.lunar_date = lunar.chinese()
    lunar_month = lunar.lunar_month
    lunar_day = lunar.lunar_day

    # 固定阳历节日
    fixed = FIXED_SOLAR.get((m, d))
    if fixed:
        add_holiday(date_meta, fixed)

    # 固定阴历节日
    lunar_fixed = FIXED_LUNAR.get((lunar_month, lunar_day))
    if lunar_fixed:
        add_holiday(date_meta, lunar_fixed)

    # 不定节日
    for (month, n, w), name in WEEKDAY_OFFSET.items():
        if m == month and d == nth_weekday(y, m, n, w):
            add_holiday(date_meta, name)

    # 二十四节气
    term = get_solar_terms(date_meta.date, date_meta.date)
    if term:
        add_holiday(date_meta, term[0][1])

    # 以下附加上特殊信息
    # 调休
    if check_lieu_day(date_meta):
        add_special_info(date_meta, "调休工作日")

    # 某个法定节日的假期
    holiday_name = get_holiday_detail(date_meta.date)[1]
    # if holiday_name is not None:
    #     add_special_info(date_meta, HOLIDAY_NAME_MAP.get(holiday_name) + "假期")

    # 假期末尾
    if holiday_name is not None and date_meta.is_holiday and is_workday(date_meta.date + timedelta(days=1)):
        add_special_info(date_meta, HOLIDAY_NAME_MAP.get(holiday_name) + "假期最后一天")

    # 极其特殊的日子
    if date_meta.date == dt(2025, 9, 3):
        date_meta.is_workday = False
        date_meta.is_holiday = True
        add_special_info(date_meta, "中国人民抗日战争暨世界反法西斯战争胜利70周年纪念日")

    # 暑假
    if m == 7 and d == 1:
        add_special_info(date_meta, "夏天的开始")

    return None


if __name__ == '__main__':
    assert is_workday(dt.today()) is True
    assert is_weekend(dt.today()) is False
    assert is_holiday(dt.today()) is False

    assert is_holiday(dt(2025, 9, 6)) is True
    assert is_holiday(dt(2025, 9, 28)) is False

    print(get_holiday_detail(dt(2025, 10, 2)))
    print(get_holiday_detail(dt(2025, 10, 18)))
    print(get_solar_terms(dt(2025, 8, 7), dt(2025, 8, 7)))

    meta = DateMeta(date=dt(2025, 8, 5))
    add_date_info(meta)
    print(meta)
