import asyncio
from typing import List

from infra.logger import logger
from .weather_scheduler import WeatherScheduler


class Pusher:
    def __init__(self, client):
        self._client = client
        self._pushers: List[WeatherScheduler | None] = []

    def start(self):
        # 1. 实例化推送器
        weather_push = WeatherScheduler(self._client)
        # 2. 启动协程
        weather_push.start()
        self._pushers.append(weather_push)
        logger.info("Pusher", "Pusher Start")

    async def stop(self):
        for p in self._pushers:
            p.stop()
        await asyncio.sleep(0)
