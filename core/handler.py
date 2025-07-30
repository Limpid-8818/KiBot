from adapter.napcat.http_api import NapCatHttpClient
from service.llm.chat import chat_handler


class Handler:
    def __init__(self, client):
        self.client: NapCatHttpClient = client

    async def reply_handler(self, group_id, msg):
        reply = await chat_handler(msg)
        await self.client.send_group_msg(group_id, reply)
