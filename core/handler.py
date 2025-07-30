from adapter.napcat.http_api import NapCatHttpClient
from infra.config.settings import Settings
from service.llm.chat import chat_handler


class Handler:
    def __init__(self, client, settings):
        self.client: NapCatHttpClient = client
        self.settings: Settings = settings

    async def reply_handler(self, group_id, msg):
        llm_config = {
            "llm_base": self.settings.LLM_BASE_URL,
            "llm_key": self.settings.LLM_API_KEY,
            "llm_model": self.settings.LLM_MODEL,
        }
        reply = await chat_handler(llm_config, msg)
        await self.client.send_group_msg(group_id, reply)
