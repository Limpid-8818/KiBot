import asyncio
import json
import os
from typing import Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.bilibili.service import BiliService
from service.bilibili.utils.screenshot import BilibiliScreenshot


class BilibiliScheduler:
    def __init__(self, http_client):
        self.service = BiliService()
        self.client: NapCatHttpClient = http_client
        self.screenshot = BilibiliScreenshot()

        # 群 -> UP主UID列表 映射
        self.subscriptions: Dict[str, List[str]] = {}
        # UP主UID -> update_baseline 映射（用于检测新动态）
        self.update_baselines: Dict[str, str] = {}

        self.subscriptions = self.load_subscriptions("cache/bilibili_subscriptions.json")
        self.update_baselines = self.load_update_baselines("cache/bilibili_update_baselines.json")
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    def subscribe(self, group_id: str, up_uid: str):
        """订阅UP主动态推送"""
        if group_id not in self.subscriptions:
            self.subscriptions[group_id] = []

        if up_uid not in self.subscriptions[group_id]:
            self.subscriptions[group_id].append(up_uid)
            self.save_subscriptions()
            logger.info("BilibiliScheduler", f"群 {group_id} 订阅了UP主 {up_uid}")

            # 订阅时立即获取一次动态，建立update_baseline
            asyncio.create_task(self._initialize_baseline(up_uid))

    def unsubscribe(self, group_id: str, up_uid: str):
        """取消订阅UP主动态推送"""
        if group_id in self.subscriptions and up_uid in self.subscriptions[group_id]:
            self.subscriptions[group_id].remove(up_uid)
            self.save_subscriptions()
            logger.info("BilibiliScheduler", f"群 {group_id} 取消订阅了UP主 {up_uid}")

    def get_subscribed_ups(self, group_id: str) -> List[str]:
        """获取群订阅的UP主列表"""
        return self.subscriptions.get(group_id, [])

    def is_subscribed(self, group_id: str, up_uid: str) -> bool:
        """检查群是否已订阅指定UP主"""
        return group_id in self.subscriptions and up_uid in self.subscriptions[group_id]

    def save_subscriptions(self):
        """保存订阅信息到文件"""
        os.makedirs("cache", exist_ok=True)
        with open("cache/bilibili_subscriptions.json", "w", encoding="utf-8") as f:
            json.dump(self.subscriptions, f, ensure_ascii=False, indent=2)

    def save_update_baselines(self):
        """保存update_baseline到文件"""
        os.makedirs("cache", exist_ok=True)
        with open("cache/bilibili_update_baselines.json", "w", encoding="utf-8") as f:
            json.dump(self.update_baselines, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_subscriptions(json_file: str) -> Dict[str, List[str]]:
        """从文件加载订阅信息"""
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_update_baselines(json_file: str) -> Dict[str, str]:
        """从文件加载update_baseline"""
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    async def _initialize_baseline(self, up_uid: str):
        """订阅时初始化baseline"""
        try:
            logger.info("BilibiliScheduler", f"为UP主 {up_uid} 初始化baseline")

            dynamics = await self.service.get_user_dynamics(int(up_uid))
            if dynamics and dynamics.data and dynamics.data.items:
                # 使用第一条动态的ID作为baseline(该 API 返回的 update_baseline为空)
                baseline = dynamics.data.items[0].id_str
                self.update_baselines[up_uid] = baseline
                self.save_update_baselines()
                logger.info("BilibiliScheduler", f"UP主 {up_uid} 的baseline已初始化: {baseline}")
            else:
                logger.warn("BilibiliScheduler", f"UP主 {up_uid} 初始化baseline失败")

        except Exception as e:
            logger.warn("BilibiliScheduler", f"初始化UP主 {up_uid} 的baseline时出错: {e}")

    async def check_new_dynamics(self, up_uid: str) -> List[str]:
        """检查UP主是否有新动态，返回新动态的截图路径列表"""
        try:
            current_baseline = self.update_baselines.get(up_uid, "")

            dynamics = await self.service.get_user_dynamics(int(up_uid))
            if not dynamics or not dynamics.data or not dynamics.data.items:
                return []

            new_screenshots = []

            latest_dynamic_id = dynamics.data.items[0].id_str
            if current_baseline != latest_dynamic_id:
                screenshot_path = await self.screenshot.fetch_dynamic_screenshot(latest_dynamic_id, mode="mobile")
                if screenshot_path:
                    new_screenshots.append(screenshot_path)

                new_baseline = latest_dynamic_id
            else:
                # 没有新动态，保持原来的baseline
                new_baseline = current_baseline

            if new_baseline is not None:
                self.update_baselines[up_uid] = new_baseline
                self.save_update_baselines()
                logger.info("BilibiliScheduler", f"UP主 {up_uid} 的baseline已更新: {new_baseline}")

            return new_screenshots

        except Exception as e:
            logger.warn("BilibiliScheduler", f"检查UP主 {up_uid} 新动态时出错: {e}")
            return []

    def start(self):
        """启动调度器"""
        # 检查调度器启动时是否存在Cookie, 在协程中执行以避免阻塞
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(self.service.ensure_valid_cookies(), loop)
        # 每5分钟检查一次新动态
        self.scheduler.add_job(
            self._check_all_subscriptions,
            trigger="interval",
            minutes=30,
            id="check_bilibili_dynamics",
        )
        self.scheduler.start()

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown(wait=True)

    async def _check_all_subscriptions(self):
        """检查所有订阅的UP主是否有新动态"""
        all_ups = set()
        for group_ups in self.subscriptions.values():
            all_ups.update(group_ups)

        for up_uid in all_ups:
            try:
                new_screenshots = await self.check_new_dynamics(up_uid)
                if new_screenshots:
                    logger.info("BilibiliScheduler", f"UP主 {up_uid} 有新动态，准备推送截图")
                    # 向所有订阅该UP主的群发送截图
                    for group_id, subscribed_ups in self.subscriptions.items():
                        if up_uid in subscribed_ups:
                            for screenshot_path in new_screenshots:
                                abs_path = os.path.abspath(screenshot_path)
                                try:
                                    # 发送图片文件
                                    await self.client.send_group_msg(int(group_id),
                                                                     f"📢 Ki酱提醒您：您关注的UP主动态更新啦"
                                                                     f"\n[CQ:image,file=file://{abs_path}]")
                                except Exception as e:
                                    logger.warn("BilibiliScheduler", f"发送动态截图到群 {group_id} 时出错: {e}")

            except Exception as e:
                logger.warn("BilibiliScheduler", f"处理UP主 {up_uid} 动态时出错: {e}")

    async def send_manual_check(self, group_id: str, up_uid: str) -> str:
        """手动检查UP主最新动态"""
        try:
            new_screenshots = await self.check_new_dynamics(up_uid)
            if new_screenshots:
                for screenshot_path in new_screenshots:
                    abs_path = os.path.abspath(screenshot_path)
                    await self.client.send_group_msg(int(group_id),
                                                     f"📢 Ki酱提醒您：您关注的UP主动态更新啦\n[CQ:image,file=file://{abs_path}]")
                return "📢 检查完毕：已发送新动态截图"
            else:
                return "📢 检查完毕：该UP主暂无新动态"
        except Exception as e:
            logger.warn("BilibiliScheduler", f"手动检查UP主 {up_uid} 动态时出错: {e}")
            return "❌ 检查动态时出现错误"
