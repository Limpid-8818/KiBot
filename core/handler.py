from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.llm.chat import LLMService
from service.weather.service import WeatherService
from service.bangumi.service import BangumiService
from core.pusher.bangumi_scheduler import BangumiScheduler


class Handler:
    def __init__(self, client):
        self.client: NapCatHttpClient = client
        self.llm_svc: LLMService = LLMService()
        self.weather_svc: WeatherService = WeatherService()
        self.bangumi_svc: BangumiService = BangumiService()
        self.bangumi_scheduler: BangumiScheduler = BangumiScheduler(self.client)

    async def reply_handler(self, group_id, msg):
        resp = await self.llm_svc.chat(msg)
        reply: str = resp.reply
        await self.client.send_group_msg(group_id, reply)

    async def weather_handler(self, group_id, msg: str):
        """
            /天气 [城市]         -> 实时天气
            /天气 预警 [城市]     -> 预警信息
        """
        default_msg = "天气服务由 和风天气 提供。\n"
        parts = msg.strip().split(maxsplit=1)
        if not parts or not parts[0]:
            logger.warn("Handler", "未指定城市")
            await self.client.send_group_msg(group_id, default_msg + "请指定城市，例如：/天气 北京")
            return

        # 判断是否以“预警”开头
        if parts[0] == "预警":
            if len(parts) == 1 or not parts[1].strip():
                await self.client.send_group_msg(group_id, default_msg + "请指定城市，例如：/天气 预警 北京")
                return
            city = parts[1].strip()
            warn_resp = await self.weather_svc.get_warning(city)
            if not warn_resp or not warn_resp.warningInfo:
                await self.client.send_group_msg(group_id, f"⚠️ 暂无「{city}」的预警信息")
                return
            alerts = "\n".join([f"⚠️ {w.title}\n{w.text}" for w in warn_resp.warningInfo])
            reply = f"🚨 {city} 气象预警\n{alerts}"
        else:
            city = parts[0]
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
    
    async def bangumi_handler(self, group_id, msg: str):
        default_msg = "番剧服务由 Bangumi 提供。\n"
        """统一处理番剧相关命令"""
        if msg.startswith("查询今日番剧放送") or msg.startswith("今日放送"):
            # 查询今日放送
            await self._handle_today_anime(group_id)
        elif msg.startswith("订阅每日番剧放送") or msg.startswith("订阅"):
            # 订阅番剧推送
            await self._handle_subscribe(group_id)
        elif msg.startswith("取消订阅每日番剧放送") or msg.startswith("取消订阅"):
            # 取消订阅番剧推送
            await self._handle_unsubscribe(group_id)
        else:
            logger.warn("Handler", "番剧指令输入不合法")
            await self.client.send_group_msg(group_id, default_msg + "请输入正确的指令，例如：/番剧 今日放送")

    async def _handle_today_anime(self, group_id):
        """处理今日放送查询"""
        anime_list = await self.bangumi_svc.get_today_anime()
        if not anime_list:
            await self.client.send_group_msg(group_id, "📺 今日暂无动画放送信息")
            return
        
        reply = "📺 今日放送\n\n"
        for anime in anime_list:
            name = anime.name_cn if anime.name_cn else anime.name
            score = f"🌟 {anime.rating.score}" if anime.rating.score > 0 else ""
            reply += f"🎬 {name} {score}\n"
            reply += f"🔗 {anime.url}\n\n"
        
        await self.client.send_group_msg(group_id, reply)

    async def _handle_subscribe(self, group_id):
        """处理订阅番剧推送"""
        self.bangumi_scheduler.subscribe(str(group_id))
        await self.client.send_group_msg(group_id, "✅ 本群已订阅每日番剧推送！每天早上8点会推送今日放送的动画信息。")

    async def _handle_unsubscribe(self, group_id):
        """处理取消订阅番剧推送"""
        self.bangumi_scheduler.unsubscribe(str(group_id))
        await self.client.send_group_msg(group_id, "❌ 本群已取消订阅每日番剧推送。")
