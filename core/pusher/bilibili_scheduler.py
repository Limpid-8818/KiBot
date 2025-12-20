import asyncio
import json
import os
from typing import Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.bilibili.service import BiliService
from service.bilibili.renderer import RenderedContent


class BilibiliScheduler:
    def __init__(self, http_client):
        self.service = BiliService()
        self.client: NapCatHttpClient = http_client

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

    async def check_new_dynamics(self, up_uid: str) -> List[RenderedContent]:
        """检查UP主是否有新动态，返回渲染后的内容列表"""
        try:
            current_baseline = self.update_baselines.get(up_uid, "")
            logger.debug("BilibiliScheduler", f"UP主 {up_uid} 当前baseline: {current_baseline}")

            dynamics = await self.service.get_user_dynamics(int(up_uid))
            if not dynamics or not dynamics.data or not dynamics.data.items:
                logger.debug("BilibiliScheduler", f"UP主 {up_uid} 获取动态为空")
                return []

            logger.debug("BilibiliScheduler", f"UP主 {up_uid} 获取到 {len(dynamics.data.items)} 条动态")

            rendered_contents = []

            for dynamic in dynamics.data.items:
                # 检查是否为新动态
                if dynamic.id_str == current_baseline:
                    logger.debug("BilibiliScheduler", f"UP主 {up_uid} 已到达baseline，停止检查")
                    break

                # 使用渲染器渲染动态内容
                content = self.service.render_dynamic(dynamic)
                rendered_contents.append(content)

            # 更新 baseline 为最新动态 ID
            if dynamics.data.items:
                new_baseline = dynamics.data.items[0].id_str
                if new_baseline != current_baseline:
                    logger.debug("BilibiliScheduler", f"UP主 {up_uid} 更新baseline: {current_baseline} -> {new_baseline}")
                self.update_baselines[up_uid] = new_baseline
                self.save_update_baselines()

            return rendered_contents

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

        if not all_ups:
            logger.info("BilibiliScheduler", "没有订阅任何UP主，跳过检查")
            return

        logger.info("BilibiliScheduler", f"开始检查 {len(all_ups)} 位UP主的动态")

        for up_uid in all_ups:
            try:
                new_contents = await self.check_new_dynamics(up_uid)
                if new_contents:
                    logger.info("BilibiliScheduler", f"UP主 {up_uid} 有 {len(new_contents)} 条新动态")
                    # 向所有订阅该UP主的群发送动态内容
                    for group_id, subscribed_ups in self.subscriptions.items():
                        if up_uid in subscribed_ups:
                            for content in new_contents:
                                await self._send_rendered_content(int(group_id), content)
                else:
                    logger.debug("BilibiliScheduler", f"UP主 {up_uid} 暂无新动态")

            except Exception as e:
                logger.warn("BilibiliScheduler", f"处理UP主 {up_uid} 动态时出错: {e}")

    async def _send_rendered_content(self, group_id: int, content: RenderedContent):
        """发送渲染后的内容到群"""
        try:
            # 构建消息段：文本 + 图片组合在一条消息中
            segments = []

            # 添加提醒前缀和动态内容
            segments.append({
                "type": "text",
                "data": {"text": f"📢 Ki酱提醒您：您关注的UP主动态更新啦\n\n{content.text}"}
            })

            # 添加图片（最多4张，内嵌在同一条消息中）
            for image_url in content.images[:4]:
                segments.append({
                    "type": "image",
                    "data": {"file": image_url}
                })

            # 使用消息段格式发送，文本和图片在同一条消息中
            await self.client.send_group_msg_with_segments(group_id, segments)

        except Exception as e:
            logger.warn("BilibiliScheduler", f"发送动态到群 {group_id} 时出错: {e}")
            # 降级：使用简单模式发送
            try:
                await self.client.send_group_msg(group_id, f"📢 Ki酱提醒您：您关注的UP主动态更新啦\n\n{content.text}")
                for image_url in content.images:
                    await self.client.send_group_msg(group_id, f"[CQ:image,file={image_url}]")
            except Exception as fallback_e:
                logger.warn("BilibiliScheduler", f"降级发送也失败: {fallback_e}")

    async def send_manual_check(self, group_id: str, up_uid: str) -> str:
        """手动检查UP主最新动态"""
        try:
            new_contents = await self.check_new_dynamics(up_uid)
            if new_contents:
                for content in new_contents:
                    await self._send_rendered_content(int(group_id), content)
                return f"📢 检查完毕：已发送 {len(new_contents)} 条新动态"
            else:
                return "📢 检查完毕：该UP主暂无新动态"
        except Exception as e:
            logger.warn("BilibiliScheduler", f"手动检查UP主 {up_uid} 动态时出错: {e}")
            return "❌ 检查动态时出现错误"
