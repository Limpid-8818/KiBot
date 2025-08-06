import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.weather.models import WarningInfo
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
    "雷阵雨": "⛈️",
    "沙尘暴": "🏜️",
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
        self.warning_cache: Dict[str, Set[str]] = {}
        self.warning_cache = self.load_warning_cache("cache/warning_cache.json")
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    def subscribe(self, group_id: str, *cities: str):
        self.subscriptions.setdefault(group_id, [])
        self.subscriptions[group_id].extend(cities)
        self.subscriptions[group_id] = list(dict.fromkeys(self.subscriptions[group_id]))  # 去重
        self.save_subscriptions("cache/weather_subscriptions.json")

    def unsubscribe(self, group_id: str, city: str):
        if group_id in self.subscriptions:
            try:
                self.subscriptions[group_id].remove(city)
            except ValueError:
                pass
            self.save_subscriptions("cache/weather_subscriptions.json")

    @staticmethod
    def load_subscriptions(json_file: str) -> Dict[str, List[str]]:
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_subscriptions(self, json_file: str):
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.subscriptions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存订阅信息失败: {e}")

    @staticmethod
    def load_warning_cache(json_file: str) -> Dict[str, Set[str]]:
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return {k: set(v) for k, v in json.load(f).items()}

    def save_warning_cache(self, json_file: str):
        # set -> list 才能序列化
        os.makedirs(os.path.dirname(json_file), exist_ok=True)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in self.warning_cache.items()}, f, ensure_ascii=False, indent=2)

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

    async def push_warning_for_group(self, group_id: str):
        cities = self.subscriptions.get(group_id, [])
        if not cities:
            return

        # 每个群有独立的缓存 set
        sent = self.warning_cache.setdefault(group_id, set())

        for city in cities:
            warn_resp = await self.service.get_warning(city)
            if not warn_resp or not warn_resp.warningInfo:
                continue

            for w in warn_resp.warningInfo:
                token = f"{w.id}@{self._calc_expire_time(w).isoformat()}"
                if token in sent:
                    continue  # 已推送过

                # 首次出现，立即推送
                msg = self._generate_warning_message(city, w)
                await self.client.send_group_msg(int(group_id), msg)
                sent.add(token)

        self.save_warning_cache("cache/warning_cache.json")

    def start(self):
        self.scheduler.add_job(
            self._send_daily_forecast,
            trigger="cron",
            hour="7",
            minute="30",
            id="push_daily_forecast",
        )
        self.scheduler.add_job(
            self._send_warnings,
            trigger="cron",
            hour="7-23",
            minute="30",
            id="push_warnings",
        )
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=True)

    async def _send_daily_forecast(self):
        self._load_new_subscriptions()
        for group_id in self.subscriptions:
            msg = await self.push_daily_forecast(group_id)
            await self.client.send_group_msg(int(group_id), msg)

    async def _send_warnings(self):
        self._load_new_subscriptions()
        self._clean_expired_warnings()
        for group_id in self.subscriptions:
            await self.push_warning_for_group(group_id)

    @staticmethod
    def _generate_warning_message(city: str, warning: WarningInfo) -> str:
        color_map = {
            "White": "⚪白色",
            "Blue": "🔵蓝色",
            "Green": "🟢绿色",
            "Yellow": "🟡黄色",
            "Orange": "🟠橙色",
            "Red": "🔴红色",
            "Black": "⚫黑色"
        }
        color = color_map.get(warning.severityColor, "无")
        level_map = {
            "Cancel": "解除",
            "None": "无",
            "Unknown": "未知",
            "Standard": "标准",
            "Minor": "轻微",
            "Moderate": "中等",
            "Major": "较重",
            "Severe": "严重",
            "Extreme": "特别严重"
        }
        level = level_map.get(warning.severity, "无")
        emoji_map = {
            "Cancel": "✅",
            "Minor": "⚠️",
            "Moderate": "😵‍💫",
            "Major": "😨",
            "Severe": "😱",
            "Extreme": "🆘"
        }
        emoji = emoji_map.get(warning.severity, "⚠️")
        warning_type_map = {
            "1001": "🌀",  # 台风
            "1002": "🌪️",  # 龙卷风
            "1003": "🌧️",  # 暴雨
            "1004": "❄️",  # 暴雪
            "1005": "🥶",  # 寒潮
            "1006": "💨",  # 大风
            "1007": "🌫️",  # 沙尘暴
            "1009": "🔥",  # 高温
            "1014": "⚡",  # 雷电
            "1015": "🧊",  # 冰雹
            "1017": "🌁",  # 大雾
            "1019": "😷",  # 霾
            "1021": "🛣️❄️",  # 道路结冰
            "1022": "🏜️",  # 干旱
            "1025": "🔥🌲",  # 森林火险
            "1031": "🌩️",  # 强对流
            "1037": "⛰️💦",  # 地质灾害气象风险
            "1041": "🔥🌿",  # 森林（草原）火险
            "1201": "🌊",  # 洪水
            "1241": "🪨💨",  # 滑坡
            "1242": "🌋",  # 泥石流
            "1272": "🌫️😷",  # 空气重污染
            "2001": "💨",  # 大风
            "2007": "🔥",  # 森林火险
            "2029": "⛈️",  # 雷暴
            "2030": "☀️🔥",  # 高温
            "2033": "🌊",  # 洪水
            "2210": "🌪️",  # 龙卷风
            "2212": "❄️🌬️",  # 暴风雪
            "2330": "🌀",  # 台风警报
            "2346": "🌪️",  # 龙卷风警报
            "2348": "🌊",  # 海啸警报
        }
        warning_type = warning_type_map.get(warning.type, "")
        opening_map = {
            "Blue": f"嘿咻～{city}的小伙伴们注意啦！Ki酱收到一条天气预警～",
            "Yellow": f"呜哇！{city}的大家注意啦！Ki酱收到一条需要留意的天气预警喵～",
            "Orange": f"大事不好啦——！{city}的大家快看！Ki酱收到一条重要预警！",
            "Red": f"紧急！紧急！{city}的小伙伴们！Ki酱收到一条超超超级严重的预警，快做好防护！"
        }
        opening = opening_map.get(warning.severityColor, f"叮叮～{city}的大家请注意！Ki酱带来一条天气消息喵～")

        lines = [
            opening,
            f"{emoji}{warning_type} {warning.typeName}",
            f"等级：{level} / 颜色：{color}",
            "",
            "预警正文:",
            warning.title,
            warning.text,
            "",
            "大家一定要注意安全哦！要是有需要帮忙的地方随时@Ki酱～(ฅ•ω•ฅ)"
        ]

        return "\n".join(lines)

    def _load_new_subscriptions(self):
        self.subscriptions = self.load_subscriptions("cache/weather_subscriptions.json")

    @staticmethod
    def _calc_expire_time(warning: WarningInfo) -> datetime:
        # 优先用 endTime
        if warning.endTime:
            return datetime.fromisoformat(warning.endTime)  # 直接解析 +08:00
        # 没有就采用24小时过期时间: startTime + 24h
        base = datetime.fromisoformat(warning.startTime)
        return base + timedelta(hours=24)

    def _clean_expired_warnings(self):
        now = datetime.now(timezone.utc)  # 统一用 UTC 比较
        removed = 0
        for group_id, id_set in self.warning_cache.items():
            to_remove = set()
            for token in id_set:
                # noinspection PyBroadException
                try:
                    _, expire_str = token.rsplit("@", 1)
                    expire_dt = datetime.fromisoformat(expire_str)
                    if expire_dt <= now:
                        to_remove.add(token)
                except Exception:
                    logger.warn("Weather", "过期时间解析失败")
                    to_remove.add(token)  # 解析失败也删
            id_set -= to_remove
            removed += len(to_remove)

        if removed:
            logger.info("Weather", f"已清理 {removed} 条过期预警缓存")
            self.save_warning_cache("cache/warning_cache.json")
