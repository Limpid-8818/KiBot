from adapter.napcat.models import GroupMessage
from infra.config.settings import Settings
from infra.logger import Logger
from adapter.napcat.ws_client import NapCatWsClient
from adapter.napcat.http_api import NapCatHttpClient
from .pusher.pusher import Pusher
from .router import Router
from .handler import Handler


class Bot:
    def __init__(self, settings, info, router, http_client, ws_client, handler, pusher):
        self.settings = settings
        self.info = info
        self.router = router
        self.http_client = http_client
        self.ws_client = ws_client
        self.handler = handler
        self.pusher = pusher

    @classmethod
    def create(cls) -> "Bot":
        settings = Settings()
        http_client = NapCatHttpClient(settings.NAPCAT_HTTP, settings.NAPCAT_HTTP_AUTH_TOKEN)
        ws_client = None
        login_info = http_client.get_login_info_sync()
        router = Router(login_info["user_id"])
        handler = Handler(http_client)
        pusher = Pusher(http_client)
        return cls(settings, login_info, router, http_client, ws_client, handler, pusher)

    async def start(self):
        """调用链：启动WebSocket客户端 -> WebSocket接收到msg -> 触发回调 -> 发送到router进行转发 -> 对应handler处理"""
        async def on_msg(msg: GroupMessage):
            Logger.info("Message received", f"[{msg.group_id}:{msg.sender.nickname}({msg.user_id})] {msg.raw_message}")
            await self.router.dispatch(msg, self.handler)

        self.ws_client = NapCatWsClient(self.settings.NAPCAT_WS, self.settings.NAPCAT_WS_AUTH_TOKEN, on_msg)

        Logger.info("BotCore", "NapCat登录账号: {}({})".format(self.info["nickname"], self.info["user_id"]))

        self.pusher.start()

        await self.ws_client.start()
