from typing import Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo

from .client import BangumiClient
from .models import CalendarDay, Subject


class BangumiService:
    def __init__(self):
        self.client = BangumiClient()

    async def get_today_anime(self) -> Optional[List[Subject]]:
        """获取今日放送的动画"""
        calendar = await self.client.get_calendar()
        if not calendar:
            return None
        
        today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).weekday()
        # Python datetime库中周一是0，周二是1，以此类推
        # Bangumi API中周一是1，周二是2，以此类推
        bangumi_weekday = today + 1 if today < 6 else 1  # 周日转换为1
        
        for day in calendar:
            if day.weekday.id == bangumi_weekday:
                return day.items
        
        return []

    async def get_weekday_anime(self, weekday_id: int) -> Optional[List[Subject]]:
        """获取指定星期的动画"""
        calendar = await self.client.get_calendar()
        if not calendar:
            return None
        
        for day in calendar:
            if day.weekday.id == weekday_id:
                return day.items
        
        return []
    
    