import re

from adapter.napcat.http_api import NapCatHttpClient
from core.pusher.weather_scheduler import WeatherScheduler
from infra.logger import logger
from service.llm.chat import LLMService
from service.weather.service import WeatherService
from service.bangumi.service import BangumiService
from core.pusher.bangumi_scheduler import BangumiScheduler
from core.pusher.bilibili_scheduler import BilibiliScheduler


class Handler:
    def __init__(self, client):
        self.client: NapCatHttpClient = client
        self.llm_svc: LLMService = LLMService()
        self.weather_svc: WeatherService = WeatherService()
        self.weather_scheduler = WeatherScheduler(self.client)
        self.bangumi_svc: BangumiService = BangumiService()
        self.bangumi_scheduler: BangumiScheduler = BangumiScheduler(self.client)
        self.bilibili_scheduler: BilibiliScheduler = BilibiliScheduler(self.client)

    async def reply_handler(self, group_id, msg, user_id):
        # resp = await self.llm_svc.chat(msg)
        resp = await self.llm_svc.chat_with_memory(msg, group_id, user_id)
        reply: str = resp.reply
        await self.client.send_group_msg(group_id, reply)

    async def weather_handler(self, group_id, msg: str):
        """
            /天气 [城市]         -> 实时天气
            /天气 预警 [城市]     -> 预警信息
            /天气 台风           -> 实时台风信息
            /天气 订阅 [城市]     -> 添加订阅城市
            /天气 取消订阅 [城市]  -> 删除订阅城市
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
        elif parts[0] == "台风":
            storm_resp = await self.weather_svc.get_storm()
            if not storm_resp:
                await self.client.send_group_msg(group_id, "⚠️🌀 当前西北太平洋无活跃热带气旋/台风")
                return

            def parse_serial(st_id: str) -> int | None:
                pattern = re.compile(r'^NP_\d{2}(\d{2})$')
                m = pattern.match(st_id)
                return int(m.group(1)) if m else None

            cyclone_level_map = {
                "TD": "热带低压",
                "TS": "热带风暴",
                "STS": "强热带风暴",
                "TY": "台风",
                "STY": "强台风",
                "SuperTY": "超强台风",
            }

            lines = []
            for idx, item in enumerate(storm_resp, 1):
                s, info = item.storm, item.stormInfo
                storm_id = parse_serial(s.id)
                # 如果move360为空，则省略括号部分
                move_dir = f"{info.moveDir}" if not info.move360 else f"{info.moveDir}({info.move360}°)"
                lines.append(
                    f"{idx}. {s.name}（{s.year}年第{storm_id}号台风）\n"
                    f"   类型：{cyclone_level_map.get(info.type, '未知')}\n"
                    f"   位置：{info.lat}°N {info.lon}°E\n"
                    f"   气压：{info.pressure} hPa\n"
                    f"   风速：{info.windSpeed} m/s\n"
                    f"   移速：{info.moveSpeed} m/s {move_dir}"
                )
            reply = f"🌀 当前西北太平洋共有{len(storm_resp)}个活跃台风\n" + "\n".join(lines)
        elif parts[0] == "订阅":
            if len(parts) == 1 or not parts[1].strip():
                await self.client.send_group_msg(group_id, default_msg + "请指定城市，例如：/天气 订阅 北京")
                return
            cities = [city.strip() for city in parts[1].strip().split()]
            for city in cities:
                if not await self.weather_svc.check_location(city):
                    await self.client.send_group_msg(group_id, f"⚠️ 未找到城市「{city}」或接口异常")
                    return
            self.weather_scheduler.subscribe(str(group_id), *cities)
            subscribed_cities = list(set(self.weather_scheduler.subscriptions.get(str(group_id), [])))
            reply = f"✅ 已成功订阅以下城市的天气更新：\n{', '.join(cities)}\n当前订阅列表：\n{', '.join(subscribed_cities)}"
        elif parts[0] == "取消订阅":
            if len(parts) == 1 or not parts[1].strip():
                await self.client.send_group_msg(group_id, default_msg + "请指定城市，例如：/天气 取消订阅 北京")
                return
            cities = [city.strip() for city in parts[1].strip().split()]
            for city in cities:
                self.weather_scheduler.unsubscribe(str(group_id), city)
            subscribed_cities = self.weather_scheduler.subscriptions.get(str(group_id), [])
            if subscribed_cities:
                reply = f"✅ 当前剩余订阅列表：\n{', '.join(subscribed_cities)}"
            else:
                reply = "✅ 当前没有订阅任何城市"
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
                f"湿度：{resp.now.humidity}%\n"
                f"风力：{resp.now.windDir} {resp.now.windScale} 级"
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

    async def bilibili_handler(self, group_id, msg: str):
        """统一处理B站订阅相关命令"""
        default_msg = "B站订阅服务。API服务为 https://socialsisteryi.github.io/bilibili-API-collect/ 项目收集而来的野生 API ，请勿滥用！\n"
        
        parts = msg.strip().split()
        if len(parts) == 0:
            await self.client.send_group_msg(group_id, default_msg + "请输入正确的指令，例如：/b站 订阅 123456")
            return
        
        command = parts[0].lower()
        
        if command == "订阅":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请指定UP主UID，例如：/b站 订阅 123456")
                return
            
            up_uid = parts[1]
            if not up_uid.isdigit():
                await self.client.send_group_msg(group_id, "❌ 请输入正确的UP主UID")
                return
            
            await self._handle_bilibili_subscribe(group_id, up_uid)
            
        elif command == "取消订阅":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请指定UP主UID，例如：/b站 取消订阅 123456")
                return
            
            up_uid = parts[1]
            if not up_uid.isdigit():
                await self.client.send_group_msg(group_id, "❌ 请输入正确的UP主UID")
                return
            
            await self._handle_bilibili_unsubscribe(group_id, up_uid)
            
        elif command == "查看订阅":
            await self._handle_bilibili_list_subscriptions(group_id)
            
        elif command == "检查":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请指定UP主UID，例如：/b站 检查 123456")
                return
            
            up_uid = parts[1]
            if not up_uid.isdigit():
                await self.client.send_group_msg(group_id, "❌ 请输入正确的UP主UID")
                return
            
            await self._handle_bilibili_check_dynamics(group_id, up_uid)
            
        else:
            await self.client.send_group_msg(group_id, default_msg + "支持的命令：订阅、取消订阅、查看订阅、检查")

    async def _handle_bilibili_subscribe(self, group_id, up_uid: str):
        """处理订阅UP主动态推送"""
        if self.bilibili_scheduler.is_subscribed(str(group_id), up_uid):
            await self.client.send_group_msg(group_id, f"⚠️ 本群已订阅UP主 {up_uid} 的动态推送")
            return
        
        self.bilibili_scheduler.subscribe(str(group_id), up_uid)
        await self.client.send_group_msg(group_id, f"✅ 本群已订阅UP主 {up_uid} 的动态推送！\n每5分钟会自动检查新动态并推送。")

    async def _handle_bilibili_unsubscribe(self, group_id, up_uid: str):
        """处理取消订阅UP主动态推送"""
        if not self.bilibili_scheduler.is_subscribed(str(group_id), up_uid):
            await self.client.send_group_msg(group_id, f"⚠️ 本群未订阅UP主 {up_uid} 的动态推送")
            return
        
        self.bilibili_scheduler.unsubscribe(str(group_id), up_uid)
        await self.client.send_group_msg(group_id, f"❌ 本群已取消订阅UP主 {up_uid} 的动态推送")

    async def _handle_bilibili_list_subscriptions(self, group_id):
        """处理查看订阅列表"""
        subscribed_ups = self.bilibili_scheduler.get_subscribed_ups(str(group_id))
        
        if not subscribed_ups:
            await self.client.send_group_msg(group_id, "📢 本群暂无订阅的UP主")
            return
        
        reply = "📢 本群订阅的UP主：\n"
        for up_uid in subscribed_ups:
            reply += f"• {up_uid}\n"
        
        await self.client.send_group_msg(group_id, reply)

    async def _handle_bilibili_check_dynamics(self, group_id, up_uid: str):
        """处理手动检查UP主动态"""
        await self.client.send_group_msg(group_id, "🔍 正在检查UP主动态...")
        
        try:
            result = await self.bilibili_scheduler.send_manual_check(str(group_id), up_uid)
            await self.client.send_group_msg(group_id, result)
        except Exception as e:
            logger.warn("Handler", f"检查UP主 {up_uid} 动态时出错: {e}")
            await self.client.send_group_msg(group_id, "❌ 检查动态时出现错误")
