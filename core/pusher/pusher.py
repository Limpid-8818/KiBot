import asyncio
from typing import List

from infra.logger import logger
from .calendar_scheduler import CalendarScheduler


class Pusher:
    def __init__(self, client, handler):
        self._client = client
        self._handler = handler
        self._pushers = []

    def start(self):
        # 复用 Handler 的调度器实例
        # 日历调度器不需要订阅管理，独立创建
        calendar_push = CalendarScheduler(self._client)

        # 启动各调度器
        self._handler.weather_scheduler.start()
        self._handler.bangumi_scheduler.start()
        self._handler.bilibili_scheduler.start()
        self._handler.live_scheduler.start()
        calendar_push.start()

        self._pushers.append(self._handler.weather_scheduler)
        self._pushers.append(self._handler.bangumi_scheduler)
        self._pushers.append(self._handler.bilibili_scheduler)
        self._pushers.append(self._handler.live_scheduler)
        self._pushers.append(calendar_push)

        logger.info("Pusher", "Pusher Start")

    async def stop(self):
        for p in self._pushers:
            p.stop()
        await asyncio.sleep(0)
