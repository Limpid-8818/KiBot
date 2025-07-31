from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.llm.chat import chat_handler
from service.weather.service import WeatherService


class Handler:
    def __init__(self, client):
        self.client: NapCatHttpClient = client
        self.weather_svc: WeatherService = WeatherService()

    async def reply_handler(self, group_id, msg):
        reply = await chat_handler(msg)
        await self.client.send_group_msg(group_id, reply)

    async def weather_handler(self, group_id, msg: str):
        city = msg
        default_msg = "天气服务由 和风天气 提供。\n"
        if city.isspace() or len(city) == 0:
            logger.warn("Handler", "未指定城市")
            await self.client.send_group_msg(group_id, default_msg + "请指定城市，例如：/天气 北京")
            return
        resp = await self.weather_svc.get_now(city)
        if not resp:
            logger.warn("Handler", "未找到城市")
            await self.client.send_group_msg(group_id, f"⚠️ 未找到城市「{city}」或接口异常")
            return
        reply = (
            f"🌤️ {resp.location.name} 实时天气\n"
            f"温度：{resp.now.temp}°C（体感 {resp.now.feelsLike}°C）\n"
            f"天气：{resp.now.text}\n"
            f"湿度：{resp.now.humidity}%"
        )
        await self.client.send_group_msg(group_id, reply)
