import json
import os
import random
from copy import deepcopy
from datetime import datetime, time, timedelta
from typing import Dict, Tuple, List
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from adapter.napcat.http_api import NapCatHttpClient
from infra.logger import logger
from service.calendar.date_utils import add_special_info
from service.calendar.models import DateMeta
from service.calendar.service import CalendarService
from service.llm.chat import LLMService


class CalendarScheduler:
    def __init__(self, http_client):
        self.service = CalendarService()
        self.llm = LLMService()
        self.client: NapCatHttpClient = http_client
        self.subscriptions: Dict[str, bool] = {}
        self.subscriptions = self.load_subscriptions("cache/calendar_subscriptions.json")
        self.group_special_days: Dict[str, List[Tuple[str, str]]] = {}
        self.group_special_days = self.load_special_days("cache/calendar_special_days.json")
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    def subscribe(self, group_id: str):
        self.subscriptions[group_id] = True
        self.save_subscriptions()

    def unsubscribe(self, group_id: str):
        if group_id in self.subscriptions:
            del self.subscriptions[group_id]
            self.save_subscriptions()

    def is_subscribed(self, group_id: str) -> bool:
        return self.subscriptions.get(group_id, False)

    def save_subscriptions(self):
        os.makedirs("cache", exist_ok=True)
        with open("cache/calendar_subscriptions.json", "w", encoding="utf-8") as f:
            json.dump(self.subscriptions, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_subscriptions(json_file: str) -> Dict[str, bool]:
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def add_special(self, group_id: str, date_str: str, content: str):
        """新增某群的某条特殊日程"""
        self.group_special_days.setdefault(group_id, [])
        self.group_special_days[group_id].append((date_str, content))
        self.save_special_days()

    def remove_special(self, group_id: str, date_str: str):
        """删除某群指定日期的特殊日程"""
        if group_id in self.group_special_days:
            self.group_special_days[group_id] = [
                (d, c) for d, c in self.group_special_days[group_id] if d != date_str
            ]
            self.save_special_days()

    def list_special(self, group_id: str) -> List[Tuple]:
        """获取某群全部特殊日程"""
        return self.group_special_days.get(group_id, [])

    def save_special_days(self):
        os.makedirs("cache", exist_ok=True)
        with open("cache/calendar_special_days.json", "w", encoding="utf-8") as f:
            # 将 tuple 转成 list，方便 JSON 序列化
            json.dump(
                {k: [list(item) for item in v] for k, v in self.group_special_days.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )

    @staticmethod
    def load_special_days(json_file: str) -> Dict[str, List[Tuple]]:
        if not os.path.exists(json_file):
            return {}
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 把 list 转回 tuple
        return {k: [tuple(item) for item in v] for k, v in data.items()}

    @staticmethod
    def _roll(probability: float = 0.7) -> bool:
        """
        按 probability(0~1) 概率返回 True/False
        """
        return random.random() < probability

    def start(self):
        self.scheduler.add_job(
            self.schedule_for_today,
            trigger="cron",
            hour=0,
            minute=30,
            id="greet_daily_plan",
            replace_existing=True,
        )
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=True)

    async def schedule_for_today(self):
        meta = self.service.today()
        logger.info("Calendar Scheduler", f"今日信息：{meta}")

        for gid in self.subscriptions:
            if not self.subscriptions[gid]:
                continue

            meta_clone = deepcopy(meta)

            specials = self.list_special(gid)
            if specials:
                filled = self.fill_specials(meta_clone, specials)
                logger.info("Calendar Scheduler", f"群 {gid} 今日特殊日程：{filled}")

            # 按照信息筛选一次
            should_send = (
                meta_clone.holiday_name is not None
                or meta_clone.special is not None
            )
            if not should_send:
                # 平常日按概率筛选
                if not self._roll(0.2):
                    logger.info("Calendar Scheduler", f"群 {gid} 今日不发送日程")
                    return

            # 确定时间点并注册任务
            base = datetime.combine(meta_clone.date, time(8, 0))
            seconds = random.randint(0, 14 * 3600)
            send_at = base + timedelta(seconds=seconds)
            logger.info("Calendar Scheduler", f"群 {gid} 日程将于{send_at}发送")

            job_id = f"greet_{gid}_{meta_clone.date.isoformat()}"
            self.scheduler.add_job(
                self._do_send,
                kwargs={'group_id': gid, 'date_meta': meta_clone},
                id=job_id,
                trigger=DateTrigger(run_date=send_at, timezone="Asia/Shanghai"),
                replace_existing=True,
            )

    @staticmethod
    def fill_specials(meta: DateMeta, specials: List[Tuple]) -> List[str]:
        today = meta.date
        specials_should_filled = []
        for date_str, content in specials:
            date_str = date_str.strip()
            # 统一按 YYYY-MM-DD 解析
            try:
                if len(date_str) == 10:  # "YYYY-MM-DD"
                    d = datetime.strptime(date_str, "%Y-%m-%d").date()
                elif len(date_str) == 5:  # "MM-DD"
                    d = datetime.strptime(date_str, "%m-%d").date().replace(year=today.year)
                else:
                    continue
            except ValueError:
                continue
            if d == today:
                specials_should_filled.append(content)

        for special_content in specials_should_filled:
            # 追加到克隆实例
            add_special_info(meta, special_content)

        return specials_should_filled

    async def _do_send(self, group_id: int, date_meta: DateMeta):
        msg = await self._build_message(date_meta)
        if msg:
            try:
                await self.client.send_group_msg(int(group_id), msg)
            except Exception as e:
                logger.warn("CalenderScheduler", f"群 {group_id} 发送失败: {e}")

    async def _build_message(self, date_meta) -> str:
        now = datetime.now(tz=ZoneInfo("Asia/Shanghai"))
        lines = [f"今天是{date_meta.date.isoformat()}, 农历{date_meta.lunar_date}。", f"现在是{now.strftime('%H:%M')}。"]

        if date_meta.is_workday and date_meta.is_weekend:
            lines.append("今天是周末，但也是工作日。")
        elif date_meta.is_workday:
            lines.append("今天是工作日。")
        elif date_meta.is_holiday:
            lines.append("今天是假期！")

        if date_meta.holiday_name:
            if type(date_meta.holiday_name) is str:
                lines.append(f"今天是节日：{date_meta.holiday_name}。")
            else:
                lines.append(f"今天是节日：{','.join(date_meta.holiday_name)}。")

        if date_meta.special:
            lines.append(f"今天也是个特殊的日子，是{','.join(date_meta.special)}。")

        content = "\n".join(lines)

        msg = await self.llm.generate_greeting(content)
        reply = msg.reply

        return reply
