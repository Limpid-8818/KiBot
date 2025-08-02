import json
import os
from datetime import datetime
from typing import Dict
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.bangumi.service import BangumiService


class BangumiScheduler:
    def __init__(self, http_client):
        self.service = BangumiService()
        self.client: NapCatHttpClient = http_client
        # 群 -> 是否订阅 映射
        self.subscriptions: Dict[str, bool] = {}
        self.subscriptions = self.load_subscriptions("cache/bangumi_subscriptions.json")
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    def subscribe(self, group_id: str):
        """订阅每日放送推送"""
        self.subscriptions[group_id] = True
        self.save_subscriptions()

    def unsubscribe(self, group_id: str):
        """取消订阅每日放送推送"""
        if group_id in self.subscriptions:
            del self.subscriptions[group_id]
            self.save_subscriptions()

    def is_subscribed(self, group_id: str) -> bool:
        """检查群是否已订阅"""
        return self.subscriptions.get(group_id, False)

    def save_subscriptions(self):
        """保存订阅信息到文件"""
        os.makedirs("cache", exist_ok=True)
        with open("cache/bangumi_subscriptions.json", "w", encoding="utf-8") as f:
            json.dump(self.subscriptions, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_subscriptions(json_file: str) -> Dict[str, bool]:
        """从文件加载订阅信息"""
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    async def push_daily_anime(self, group_id: str) -> str:
        """生成每日放送推送消息"""
        if not self.is_subscribed(group_id):
            return ""

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai"))
        formatted_date = f"{today.month}月{today.day}日"
        
        # 获取今日放送的动画
        anime_list = await self.service.get_today_anime()
        
        if not anime_list:
            return f"📺 今日({formatted_date})\n\n暂无动画放送信息"

        lines = [f"📺 !今日({formatted_date})放送表!"]
        
        for anime in anime_list:
            # 构建动画信息
            name = anime.name_cn if anime.name_cn else anime.name
            score = f"🌟 {anime.rating.score}" if anime.rating.score > 0 else ""
            
            anime_info = f"🎬 {name}"
            if score:
                anime_info += f" {score}"
            
            lines.append(anime_info)
            lines.append(f"🔗 {anime.url}")
            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def start(self):
        """启动调度器"""
        # 每天早上8点推送
        self.scheduler.add_job(
            self._send_daily_anime,
            trigger="cron",
            hour="8",
            minute="00",
            id="push_daily_anime",
        )
        self.scheduler.start()

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown(wait=True)

    async def _send_daily_anime(self):
        """发送每日放送信息到所有订阅的群"""
        for group_id in self.subscriptions:
            if self.subscriptions[group_id]:
                try:
                    msg = await self.push_daily_anime(group_id)
                    if msg:
                        await self.client.send_group_msg(int(group_id), msg)
                except Exception as e:
                    logger.warn("BangumiScheduler", f"发送每日放送到群 {group_id} 时出错: {e}")

    async def send_manual_push(self, group_id: str) -> str:
        """手动发送每日放送信息"""
        return await self.push_daily_anime(group_id)
