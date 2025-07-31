import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapter.napcat.http_api import NapCatHttpClient
from service.weather.service import WeatherService

EMOJI_MAP = {
    "晴": "☀️",
    "多云": "⛅",
    "阴": "☁️",
    "小雨": "🌦️",
    "中雨": "🌧️",
    "大雨": "🌧️",
    "暴雨": "⛈️",
    "雪": "❄️",
    "雾": "🌫️",
    "霾": "🌫️",
}


def _emoji(text: str) -> str:
    for k, v in EMOJI_MAP.items():
        if k in text:
            return v
    return ""


class WeatherScheduler:
    def __init__(self, http_client):
        self.service = WeatherService()
        self.client: NapCatHttpClient = http_client
        # 群 -> 关注城市 映射
        self.subscriptions: Dict[str, List[str]] = {}
        self.subscriptions = self.load_subscriptions("cache/weather_subscriptions.json")
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    def subscribe(self, group_id: str, *cities: str):
        self.subscriptions.setdefault(group_id, []).extend(cities)

    def unsubscribe(self, group_id: str, city: str):
        if group_id in self.subscriptions:
            try:
                self.subscriptions[group_id].remove(city)
            except ValueError:
                pass

    @staticmethod
    def load_subscriptions(json_file: str) -> Dict[str, List[str]]:
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    async def push_daily_forecast(self, group_id: str) -> str:
        cities = self.subscriptions.get(group_id, [])
        if not cities:
            return ""

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai"))
        formatted_date = f"{today.month}月{today.day}日"

        lines = ["📅 *今日天气播报* " + formatted_date]
        for city in cities:
            resp = await self.service.get_today(city)
            if not resp or not resp.daily:
                lines.append(f"⚠️ {city}：获取失败")
                continue

            f = resp.daily[0]
            emoji_day = _emoji(f.textDay)
            emoji_night = _emoji(f.textNight)
            lines.append(
                f"{emoji_day} {resp.location.name}\n"
                f"🌅 日间 {emoji_day}{f.textDay} / 🌃 夜间 {emoji_night}{f.textNight}\n"
                f"🌡️ {f.tempMin}°C ~ {f.tempMax}°C\n"
                f"💨 {f.windDirDay} {f.windScaleDay} 级"
            )

        return "\n\n".join(lines)

    def start(self):
        self.scheduler.add_job(
            self._send_daily_forecast,
            trigger="cron",
            hour="8",
            minute="00",
            id="push_daily_forecast",
        )
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=True)

    async def _send_daily_forecast(self):
        for group_id in self.subscriptions:
            msg = await self.push_daily_forecast(group_id)
            await self.client.send_group_msg(int(group_id), msg)


# ---------- 测试环境 ----------
async def _test():
    # 2. 初始化 HttpClient
    http_client = NapCatHttpClient("http://39.105.118.24:3000")  # NapCat 默认地址

    ws = WeatherScheduler(http_client)

    # 4. 订阅测试城市
    ws.subscribe("947826617", "北京", "上海")

    # # 5. 立即手动触发一次
    # await ws.send_daily_forecast()
    # print("✅ 手动推送完成")

    # 6. 可选：启动调度器，等到 00:00 再次触发
    ws.start()
    print("🕛 已启动定时器，等待自动推送")
    try:
        await asyncio.Event().wait()   # 一直挂着
    except KeyboardInterrupt:
        ws.stop()

if __name__ == "__main__":
    asyncio.run(_test())
