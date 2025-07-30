import re

from adapter.napcat.models import GroupMessage
from core.handler import Handler


class Router:
    def __init__(self, qq_id: str):
        self._bot_qq = qq_id
        self._at_re = re.compile(rf"\[CQ:at,qq={qq_id}\]")

    async def dispatch(self, message: GroupMessage, handler: Handler):
        if not self.should_reply(message):
            return None
        cleaned_msg = self.clean_text(message)
        await handler.reply_handler(message.group_id, cleaned_msg)

    def should_reply(self, msg: GroupMessage) -> bool:
        return self._at_re.search(msg.raw_message) is not None

    def clean_text(self, msg: GroupMessage) -> str:
        return self._at_re.sub("", msg.raw_message).strip()
