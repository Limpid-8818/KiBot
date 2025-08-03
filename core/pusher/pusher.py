import asyncio
from typing import List

from infra.logger import logger
from .weather_scheduler import WeatherScheduler
from .bangumi_scheduler import BangumiScheduler
from .bilibili_scheduler import BilibiliScheduler


class Pusher:
    def __init__(self, client):
        self._client = client
        self._pushers: List[WeatherScheduler | BangumiScheduler | BilibiliScheduler | None] = []

    def start(self):
        # 1. 实例化推送器
        weather_push = WeatherScheduler(self._client)
        bangumi_push = BangumiScheduler(self._client)
        bilibili_push = BilibiliScheduler(self._client)
        
        # 2. 启动协程
        weather_push.start()
        bangumi_push.start()
        bilibili_push.start()
        
        self._pushers.append(weather_push)
        self._pushers.append(bangumi_push)
        self._pushers.append(bilibili_push)
        
        logger.info("Pusher", "Pusher Start")

    async def stop(self):
        for p in self._pushers:
            p.stop()
        await asyncio.sleep(0)
