import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

from adapter.napcat.http_api import NapCatHttpClient
from core.pusher.bangumi_scheduler import BangumiScheduler
from core.pusher.bilibili_scheduler import BilibiliScheduler
from core.pusher.live_scheduler import LiveScheduler
from core.pusher.weather_scheduler import WeatherScheduler
from infra.logger import logger
from service.bangumi.service import BangumiService
from service.bilibili.service import BiliService
from service.llm.chat import LLMService
from service.weather.service import WeatherService


class Handler:
    def __init__(self, client):
        self.client: NapCatHttpClient = client
        self.llm_svc: LLMService = LLMService()
        self.weather_svc: WeatherService = WeatherService()
        self.weather_scheduler = WeatherScheduler(self.client)
        self.bangumi_svc: BangumiService = BangumiService()
        self.bangumi_scheduler: BangumiScheduler = BangumiScheduler(self.client)
        self.bilibili_scheduler: BilibiliScheduler = BilibiliScheduler(self.client)
        self.bilibili_svc: BiliService = BiliService()
        self.live_scheduler: LiveScheduler = LiveScheduler(self.client)

    async def reply_handler(self, group_id, msg, user_id):
        # resp = await self.llm_svc.chat(msg)
        # resp = await self.llm_svc.chat_with_memory(msg, group_id, user_id)
        resp = await self.llm_svc.agent_chat(msg, group_id, user_id)
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
                s, info = item[0].storm, item[0].stormInfo
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
            await self.client.send_group_msg(group_id, reply)

            # 绘制台风路径图
            await self.client.send_group_msg(group_id, "希酱正在努力绘制台风路径图，请稍等哦~")

            executor = ThreadPoolExecutor(max_workers=2)

            def _render_sync(storm_data) -> str | None:
                try:
                    return self.weather_svc.render_storm(storm_data)
                except Exception as e:
                    logger.error("Weather", f"绘制台风路径时出现错误：{e}")
                    return None

            futures = [
                asyncio.get_running_loop().run_in_executor(executor, _render_sync, single_storm)
                for single_storm in storm_resp
            ]

            img_paths = await asyncio.gather(*futures)

            for single_storm, img_path in zip(storm_resp, img_paths):
                typhoon_name = single_storm[0].storm.name
                if img_path:
                    logger.info("Weather", f"台风「{typhoon_name}」路径已绘制，保存于{img_path}")
                    await self.client.send_group_image_msg(group_id, img_path)
                else:
                    logger.warn("Weather", f"台风「{typhoon_name}」路径绘制失败")

            return
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

        elif command == "视频":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请提供视频 BV 号，例如：/b站 视频 BV1xx411c7mD")
                return
            await self._handle_video_info(group_id, parts[1])

        elif command == "up主":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请提供 UP主 UID，例如：/b站 UP主 123456")
                return
            await self._handle_user_info(group_id, parts[1])

        # 直播相关命令
        elif command == "直播订阅":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请指定UP主UID，例如：/b站 直播订阅 123456")
                return
            up_uid = parts[1]
            if not up_uid.isdigit():
                await self.client.send_group_msg(group_id, "❌ 请输入正确的UP主UID")
                return
            await self._handle_live_subscribe(group_id, up_uid)

        elif command == "直播取消":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请指定UP主UID，例如：/b站 直播取消 123456")
                return
            up_uid = parts[1]
            if not up_uid.isdigit():
                await self.client.send_group_msg(group_id, "❌ 请输入正确的UP主UID")
                return
            await self._handle_live_unsubscribe(group_id, up_uid)

        elif command == "直播列表":
            await self._handle_live_list_subscriptions(group_id)

        elif command == "直播状态":
            if len(parts) < 2:
                await self.client.send_group_msg(group_id, "❌ 请指定UP主UID，例如：/b站 直播状态 123456")
                return
            up_uid = parts[1]
            if not up_uid.isdigit():
                await self.client.send_group_msg(group_id, "❌ 请输入正确的UP主UID")
                return
            await self._handle_live_status(group_id, up_uid)

        else:
            await self.client.send_group_msg(group_id, default_msg + "支持的命令：订阅、取消订阅、查看订阅、检查、视频、UP主、直播订阅、直播取消、直播列表、直播状态")

    async def _handle_bilibili_subscribe(self, group_id, up_uid: str):
        """处理订阅UP主动态推送"""
        if self.bilibili_scheduler.is_subscribed(str(group_id), up_uid):
            await self.client.send_group_msg(group_id, f"⚠️ 本群已订阅UP主 {up_uid} 的动态推送")
            return
        
        self.bilibili_scheduler.subscribe(str(group_id), up_uid)
        await self.client.send_group_msg(group_id,
                                         f"✅ 本群已订阅UP主 {up_uid} 的动态推送！\n每5分钟会自动检查新动态并推送。")

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

    async def _handle_video_info(self, group_id, bvid: str):
        """处理视频信息查询"""
        video = await self.bilibili_svc.get_video_info(bvid=bvid)
        if not video:
            await self.client.send_group_msg(group_id, f"❌ 未找到视频: {bvid}")
            return

        content = self.bilibili_svc.render_video(video)

        try:
            # 使用消息段格式发送，文本和封面在同一条消息中
            segments = content.to_segments()
            await self.client.send_group_msg_with_segments(group_id, segments)
        except Exception as e:
            # 降级：使用简单模式发送
            await self.client.send_group_msg(group_id, content.text)
            for image_url in content.images:
                await self.client.send_group_msg(group_id, f"[CQ:image,file={image_url}]")

    async def _handle_user_info(self, group_id, mid_str: str):
        """处理 UP主 信息查询"""
        try:
            mid = int(mid_str)
        except ValueError:
            await self.client.send_group_msg(group_id, "❌ UID 格式错误，请输入数字")
            return

        user = await self.bilibili_svc.get_user_info(mid)
        if not user:
            await self.client.send_group_msg(group_id, f"❌ 未找到 UP主: {mid}")
            return

        info = user.info
        stat = user.stat
        text = f"""👤 {info.name}
🆔 UID: {info.mid}
📝 {info.sign or '这个人很懒，什么都没写'}

👥 粉丝: {stat.follower}
➕ 关注: {stat.following}"""

        try:
            # 使用消息段格式发送，文本和头像在同一条消息中
            segments = [{"type": "text", "data": {"text": text}}]
            if info.face:
                segments.append({"type": "image", "data": {"file": info.face}})
            await self.client.send_group_msg_with_segments(group_id, segments)
        except Exception as e:
            # 降级：使用简单模式发送
            await self.client.send_group_msg(group_id, text)
            if info.face:
                await self.client.send_group_msg(group_id, f"[CQ:image,file={info.face}]")

    async def _handle_live_subscribe(self, group_id, up_uid: str):
        """处理直播订阅"""
        group_id_str = str(group_id)

        if self.live_scheduler.is_subscribed(group_id_str, up_uid):
            await self.client.send_group_msg(group_id, f"❌ 已订阅 UP主 {up_uid} 的直播")
            return

        # 验证UP主是否存在
        user = await self.bilibili_svc.get_user_info(int(up_uid))
        if not user:
            await self.client.send_group_msg(group_id, f"❌ 未找到 UP主 {up_uid}")
            return

        self.live_scheduler.subscribe(group_id_str, up_uid)
        await self.client.send_group_msg(group_id, f"✅ 已订阅 {user.info.name} 的直播通知\n当 TA 开播时会第一时间通知您！")

    async def _handle_live_unsubscribe(self, group_id, up_uid: str):
        """处理取消直播订阅"""
        group_id_str = str(group_id)

        if not self.live_scheduler.is_subscribed(group_id_str, up_uid):
            await self.client.send_group_msg(group_id, f"❌ 未订阅 UP主 {up_uid} 的直播")
            return

        self.live_scheduler.unsubscribe(group_id_str, up_uid)
        await self.client.send_group_msg(group_id, f"✅ 已取消订阅 UP主 {up_uid} 的直播通知")

    async def _handle_live_list_subscriptions(self, group_id):
        """处理查看直播订阅列表"""
        group_id_str = str(group_id)
        subscribed_ups = self.live_scheduler.get_subscribed_ups(group_id_str)

        if not subscribed_ups:
            await self.client.send_group_msg(group_id, "📺 本群暂无直播订阅")
            return

        msg = f"📺 本群已订阅 {len(subscribed_ups)} 位 UP主 的直播：\n"

        for up_uid in subscribed_ups:
            # 获取UP主信息
            user = await self.bilibili_svc.get_user_info(int(up_uid))
            if user:
                msg += f"  • {user.info.name} (UID: {up_uid})\n"
            else:
                msg += f"  • UID: {up_uid}\n"

        await self.client.send_group_msg(group_id, msg.strip())

    async def _handle_live_status(self, group_id, up_uid: str):
        """处理查询直播状态"""
        room_info = await self.live_scheduler.check_live_status(up_uid)

        if not room_info:
            await self.client.send_group_msg(group_id, f"❌ 查询 UP主 {up_uid} 直播状态失败")
            return

        if room_info.is_living:
            text = f"""🔴 正在直播

👤 {room_info.uname}
📺 {room_info.title}
🎮 分区: {room_info.area_v2_parent_name} · {room_info.area_v2_name}
👥 人气: {room_info.online}

🔗 {room_info.live_url}"""
        else:
            text = f"""⚫ 未开播

👤 {room_info.uname}
📺 上次直播: {room_info.title or '暂无'}

🔗 {room_info.live_url}"""

        try:
            segments = [{"type": "text", "data": {"text": text}}]
            if room_info.cover:
                segments.append({"type": "image", "data": {"file": room_info.cover}})
            await self.client.send_group_msg_with_segments(group_id, segments)
        except Exception:
            await self.client.send_group_msg(group_id, text)

    async def help_handler(self, group_id, help_cmd: str):
        """处理帮助请求，根据指定的模块返回详细帮助信息"""
        greet_msg = (
            "你好呀！😉👋我是你的好伙伴希酱\n"
            "不知道希酱能为你做什么？请看……\n"
        )
        # 基础帮助信息
        base_help = (
            "📝 KiBot 帮助中心\n"
            "使用格式：@我 + /命令 [参数]\n"
            "可用功能：天气、番剧、B站、帮助\n"
            "示例：@我 /天气 北京  或  @我 /帮助 天气\n\n"
        )

        # 天气模块帮助
        weather_help = (
            "🌤️ 天气命令\n"
            "/天气 [城市]         → 查询指定城市实时天气\n"
            "/天气 预警 [城市]     → 查询指定城市气象预警\n"
            "/天气 台风           → 查询西北太平洋活跃台风\n"
            "/天气 订阅 [城市]     → 订阅指定城市天气推送（每日7:30）\n"
            "/天气 取消订阅 [城市]  → 取消指定城市天气订阅\n"
            "示例：\n"
            "  /天气 上海\n"
            "  /天气 预警 上海\n"
            "  /天气 订阅 上海 北京\n"
        )

        # 番剧模块帮助
        bangumi_help = (
            "📺 番剧命令\n"
            "/番剧 今日放送       → 查询今日动画放送信息\n"
            "/番剧 订阅           → 订阅每日番剧推送（每天8:00）\n"
            "/番剧 取消订阅       → 取消每日番剧推送\n"
        )

        # B站模块帮助
        bilibili_help = (
            "📺 B站命令\n"
            "【动态订阅】\n"
            "/b站 订阅 [UID]          → 订阅UP主动态推送（每30分钟检查）\n"
            "/b站 取消订阅 [UID]      → 取消UP主动态订阅\n"
            "/b站 查看订阅            → 查看本群动态订阅列表\n"
            "/b站 检查 [UID]          → 手动检查UP主最新动态\n"
            "\n【直播订阅】\n"
            "/b站 直播订阅 [UID]      → 订阅UP主开播提醒（每2分钟检查）\n"
            "/b站 直播取消 [UID]      → 取消UP主直播订阅\n"
            "/b站 直播列表            → 查看本群直播订阅列表\n"
            "/b站 直播状态 [UID]      → 查询UP主当前直播状态\n"
            "\n【信息查询】\n"
            "/b站 视频 [BV号]         → 查询视频详细信息\n"
            "/b站 UP主 [UID]          → 查询UP主信息\n"
            "示例：\n"
            "  /b站 订阅 123456\n"
            "  /b站 直播订阅 123456\n"
            "  /b站 视频 BV1xx411c7mD\n"
        )

        if not help_cmd:
            # 无指定模块，返回基础帮助+模块列表
            full_help = greet_msg + base_help + (
                "🔍 查看模块详情：\n"
                "  /帮助 天气   → 查看天气功能详细说明\n"
                "  /帮助 番剧   → 查看番剧功能详细说明\n"
                "  /帮助 B站    → 查看B站功能详细说明\n"
                "\n"
                "如果想要和我聊天的话，直接@我就可以啦！\n"
                "大家和我说的每一句话，我都会努力记住的！😊"
            )
        elif help_cmd == "天气":
            full_help = base_help + weather_help
        elif help_cmd in ["番剧", "动画"]:
            full_help = base_help + bangumi_help
        elif help_cmd in ["B站", "b站", "哔哩哔哩"]:
            full_help = base_help + bilibili_help
        else:
            full_help = base_help + f"❓ 未找到「{help_cmd}」模块的帮助信息\n请输入正确的模块名称"

        await self.client.send_group_msg(group_id, full_help)
