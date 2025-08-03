import re

from adapter.napcat.models import GroupMessage
from core.handler import Handler


class Router:
    def __init__(self, qq_id: str):
        self._bot_qq = qq_id
        self._at_re = re.compile(rf"\[CQ:at,qq={qq_id}]")

    async def dispatch(self, message: GroupMessage, handler: Handler):
        if not self.should_reply(message):
            return None
        cleaned_msg = self.clean_text(message)
        # 命令分发
        if cleaned_msg.startswith("/天气"):
            result_msg = re.sub(r'^/天气\s?', '', cleaned_msg)
            await handler.weather_handler(message.group_id, result_msg)
        elif cleaned_msg.startswith("/番剧"):
            bangumi_cmd = re.sub(r'^/番剧\s?', '', cleaned_msg).strip()
            await handler.bangumi_handler(message.group_id, bangumi_cmd)
        elif cleaned_msg.startswith("/b站"):
            bilibili_cmd = re.sub(r'^/b站\s?', '', cleaned_msg).strip()
            await handler.bilibili_handler(message.group_id, bilibili_cmd)
        else:
            await handler.reply_handler(message.group_id, cleaned_msg)

    def should_reply(self, msg: GroupMessage) -> bool:
        return self._at_re.search(msg.raw_message) is not None

    def clean_text(self, msg: GroupMessage) -> str:
        return self._at_re.sub("", msg.raw_message).strip()
