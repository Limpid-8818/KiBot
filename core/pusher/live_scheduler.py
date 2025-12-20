"""B站直播订阅调度器"""

import asyncio
import json
import os
from typing import Dict, List, Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.bilibili.client import BiliClient
from service.bilibili.models import LiveRoomInfo


class LiveScheduler:
    """B站直播订阅调度器"""

    def __init__(self, http_client: NapCatHttpClient):
        self.client: NapCatHttpClient = http_client
        self.bili_client = BiliClient()

        # 群 -> UP主UID列表 映射
        self.subscriptions: Dict[str, List[str]] = {}
        # UP主UID -> 是否正在直播 映射（用于检测开播）
        self.live_status: Dict[str, bool] = {}

        self.subscriptions = self._load_subscriptions("cache/live_subscriptions.json")
        self.live_status = self._load_live_status("cache/live_status.json")
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    def subscribe(self, group_id: str, up_uid: str) -> bool:
        """订阅UP主直播通知"""
        if group_id not in self.subscriptions:
            self.subscriptions[group_id] = []

        if up_uid in self.subscriptions[group_id]:
            return False  # 已订阅

        self.subscriptions[group_id].append(up_uid)
        self._save_subscriptions()
        logger.info("LiveScheduler", f"群 {group_id} 订阅了UP主 {up_uid} 的直播")

        # 初始化直播状态（防止首次运行时误推送）
        asyncio.create_task(self._initialize_live_status(up_uid))
        return True

    def unsubscribe(self, group_id: str, up_uid: str) -> bool:
        """取消订阅UP主直播通知"""
        if group_id not in self.subscriptions:
            return False
        if up_uid not in self.subscriptions[group_id]:
            return False

        self.subscriptions[group_id].remove(up_uid)
        self._save_subscriptions()
        logger.info("LiveScheduler", f"群 {group_id} 取消订阅了UP主 {up_uid} 的直播")
        return True

    def get_subscribed_ups(self, group_id: str) -> List[str]:
        """获取群订阅的UP主列表"""
        return self.subscriptions.get(group_id, [])

    def is_subscribed(self, group_id: str, up_uid: str) -> bool:
        """检查群是否已订阅指定UP主直播"""
        return group_id in self.subscriptions and up_uid in self.subscriptions[group_id]

    def _save_subscriptions(self):
        """保存订阅信息到文件"""
        os.makedirs("cache", exist_ok=True)
        with open("cache/live_subscriptions.json", "w", encoding="utf-8") as f:
            json.dump(self.subscriptions, f, ensure_ascii=False, indent=2)

    def _save_live_status(self):
        """保存直播状态到文件"""
        os.makedirs("cache", exist_ok=True)
        with open("cache/live_status.json", "w", encoding="utf-8") as f:
            json.dump(self.live_status, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _load_subscriptions(json_file: str) -> Dict[str, List[str]]:
        """从文件加载订阅信息"""
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _load_live_status(json_file: str) -> Dict[str, bool]:
        """从文件加载直播状态"""
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    async def _initialize_live_status(self, up_uid: str):
        """初始化UP主的直播状态"""
        try:
            room_info = await self.bili_client.get_live_room_by_mid(int(up_uid))
            if room_info:
                self.live_status[up_uid] = room_info.is_living
                self._save_live_status()
                logger.info("LiveScheduler", f"UP主 {up_uid} 直播状态已初始化: {'直播中' if room_info.is_living else '未开播'}")
        except Exception as e:
            logger.warn("LiveScheduler", f"初始化UP主 {up_uid} 直播状态时出错: {e}")

    def start(self):
        """启动调度器"""
        # 每2分钟检查一次直播状态
        self.scheduler.add_job(
            self._check_all_live_status,
            trigger="interval",
            minutes=2,
            id="check_live_status",
        )
        self.scheduler.start()
        logger.info("LiveScheduler", "直播订阅调度器已启动")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown(wait=True)

    async def _check_all_live_status(self):
        """检查所有订阅的UP主是否开播"""
        # 收集所有订阅的UP主UID
        all_uids: Set[int] = set()
        for group_ups in self.subscriptions.values():
            all_uids.update(int(uid) for uid in group_ups)

        if not all_uids:
            return

        try:
            # 批量查询直播状态
            live_info_map = await self.bili_client.get_live_status_by_uids(list(all_uids))

            for uid, room_info in live_info_map.items():
                uid_str = str(uid)
                was_living = self.live_status.get(uid_str, False)
                is_living = room_info.is_living

                # 检测开播（从未开播变为直播中）
                if is_living and not was_living:
                    logger.info("LiveScheduler", f"UP主 {room_info.uname}({uid}) 开播了: {room_info.title}")
                    # 向所有订阅该UP主的群发送开播通知
                    for group_id, subscribed_ups in self.subscriptions.items():
                        if uid_str in subscribed_ups:
                            await self._send_live_notification(int(group_id), room_info)

                # 更新状态
                self.live_status[uid_str] = is_living

            self._save_live_status()

        except Exception as e:
            logger.warn("LiveScheduler", f"检查直播状态时出错: {e}")

    async def _send_live_notification(self, group_id: int, room_info: LiveRoomInfo):
        """发送开播通知到群"""
        try:
            # 构建消息段
            segments = []

            # 文本内容
            text = f"""🔴 直播开播提醒

👤 {room_info.uname} 开播啦！
📺 {room_info.title}
🎮 分区: {room_info.area_v2_parent_name} · {room_info.area_v2_name}
👥 人气: {room_info.online}

🔗 {room_info.live_url}"""

            segments.append({
                "type": "text",
                "data": {"text": text}
            })

            # 添加封面图
            if room_info.cover:
                segments.append({
                    "type": "image",
                    "data": {"file": room_info.cover}
                })

            await self.client.send_group_msg_with_segments(group_id, segments)

        except Exception as e:
            logger.warn("LiveScheduler", f"发送开播通知到群 {group_id} 时出错: {e}")
            # 降级发送
            try:
                text = f"🔴 {room_info.uname} 开播啦！\n📺 {room_info.title}\n🔗 {room_info.live_url}"
                await self.client.send_group_msg(group_id, text)
            except Exception as fallback_e:
                logger.warn("LiveScheduler", f"降级发送也失败: {fallback_e}")

    async def check_live_status(self, up_uid: str) -> LiveRoomInfo | None:
        """手动查询UP主直播状态"""
        try:
            result = await self.bili_client.get_live_status_by_uids([int(up_uid)])
            return result.get(int(up_uid))
        except Exception as e:
            logger.warn("LiveScheduler", f"查询UP主 {up_uid} 直播状态时出错: {e}")
            return None
