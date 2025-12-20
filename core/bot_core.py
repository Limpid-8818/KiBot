from typing import Optional

import uvicorn

from adapter.napcat.models import GroupMessage
from infra.config.settings import Settings
from infra.logger import Logger
from adapter.napcat.webhook_server import WebhookServer
from adapter.napcat.ws_client import NapCatWsClient
from adapter.napcat.http_api import NapCatHttpClient
from .pusher.pusher import Pusher
from .router import Router
from .handler import Handler


class Bot:
    def __init__(
        self,
        settings: Settings,
        info: dict,
        router: Router,
        http_client: NapCatHttpClient,
        handler: Handler,
        pusher: Pusher,
        webhook_server: Optional[WebhookServer] = None,
        ws_client: Optional[NapCatWsClient] = None,
    ):
        self.settings = settings
        self.info = info
        self.router = router
        self.http_client = http_client
        self.handler = handler
        self.pusher = pusher
        self.webhook_server = webhook_server
        self.ws_client = ws_client

    @classmethod
    def create(cls) -> "Bot":
        settings = Settings()
        http_client = NapCatHttpClient(settings.NAPCAT_HTTP, settings.NAPCAT_HTTP_AUTH_TOKEN)
        login_info = http_client.get_login_info_sync()
        router = Router(login_info["user_id"])
        handler = Handler(http_client)
        pusher = Pusher(http_client, handler)

        # 创建消息处理回调函数
        async def on_msg(msg: GroupMessage):
            Logger.info("Message received", f"[{msg.group_id}:{msg.sender.nickname}({msg.user_id})] {msg.raw_message}")
            await router.dispatch(msg, handler)

        webhook_server = None
        ws_client = None

        if settings.CONNECTION_MODE == "webhook":
            # 创建 Webhook 服务器
            webhook_server = WebhookServer(
                secret_token=settings.NAPCAT_WEBHOOK_SECRET,
                message_handler=on_msg
            )
        else:
            # 创建 WebSocket 客户端
            ws_client = NapCatWsClient(
                ws_url=settings.NAPCAT_WS,
                auth_token=settings.NAPCAT_WS_AUTH_TOKEN,
                handler=on_msg
            )

        return cls(
            settings=settings,
            info=login_info,
            router=router,
            http_client=http_client,
            handler=handler,
            pusher=pusher,
            webhook_server=webhook_server,
            ws_client=ws_client,
        )

    def start_pusher(self):
        """启动定时推送任务"""
        Logger.info("BotCore", "NapCat登录账号: {}({})".format(self.info["nickname"], self.info["user_id"]))
        self.pusher.start()
        Logger.info("BotCore", "Pusher started")

    async def run(self):
        """根据配置的连接模式启动服务"""
        if self.settings.CONNECTION_MODE == "webhook":
            await self._run_webhook()
        else:
            await self._run_websocket()

    async def _run_webhook(self):
        """启动 Webhook 服务器"""
        if not self.webhook_server:
            raise RuntimeError("Webhook server not initialized")

        config = uvicorn.Config(
            app=self.webhook_server.get_app(),
            host=self.settings.WEBHOOK_HOST,
            port=self.settings.WEBHOOK_PORT,
            log_level="info",
            access_log=True,
        )
        server = uvicorn.Server(config)

        Logger.info("Main", f"Starting KiBot in WEBHOOK mode")
        Logger.info("Main", f"Webhook server on {self.settings.WEBHOOK_HOST}:{self.settings.WEBHOOK_PORT}")
        Logger.info("Main", f"Webhook endpoint: http://{self.settings.WEBHOOK_HOST}:{self.settings.WEBHOOK_PORT}/webhook")

        await server.serve()

    async def _run_websocket(self):
        """启动 WebSocket 客户端"""
        if not self.ws_client:
            raise RuntimeError("WebSocket client not initialized")

        Logger.info("Main", f"Starting KiBot in WEBSOCKET mode")
        Logger.info("Main", f"Connecting to {self.settings.NAPCAT_WS}")

        await self.ws_client.start()
