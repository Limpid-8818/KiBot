import datetime

from service.calendar.date_utils import add_date_info
from service.calendar.models import DateMeta


class CalendarService:
    @staticmethod
    def _fetch_day(date: datetime.date) -> DateMeta:
        meta = DateMeta(date=date)
        add_date_info(meta)
        return meta

    def today(self) -> DateMeta:
        today = datetime.date.today()
        return self._fetch_day(today)

    def get_day(self, date: datetime.date) -> DateMeta:
        return self._fetch_day(date)
