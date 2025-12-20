"""
NapCat Webhook 服务器模块

接收 NapCat 通过 HTTP POST 推送的事件，并分发给对应的 handler 处理。
"""
import asyncio
import hmac
import hashlib
from typing import Optional, Callable, Awaitable

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

from adapter.napcat.models import GroupMessage
from infra.logger import Logger

# 定义消息处理器类型
MessageHandler = Callable[[GroupMessage], Awaitable[None]]


class WebhookServer:
    """
    NapCat Webhook 服务器

    接收来自 NapCat HTTP 客户端的事件推送，验证 token 后分发给消息处理器。
    """

    def __init__(self, secret_token: str, message_handler: MessageHandler):
        """
        初始化 Webhook 服务器

        Args:
            secret_token: 用于验证请求的密钥，应与 NapCat 配置中的 token 一致
            message_handler: 处理消息的回调函数
        """
        self.secret_token = secret_token
        self.message_handler = message_handler
        self.app = FastAPI(title="KiBot Webhook Server")

        # 注册路由
        self._setup_routes()

        Logger.info("WebhookServer", f"Initialized with token verification: {bool(secret_token)}")

    def _setup_routes(self):
        """设置 FastAPI 路由"""

        @self.app.post("/webhook")
        async def handle_webhook(
            request: Request,
            authorization: Optional[str] = Header(None),
            x_signature: Optional[str] = Header(None)
        ):
            """
            处理 NapCat HTTP POST 事件上报

            NapCat 会将所有事件通过 HTTP POST 发送到这个端点。
            事件格式遵循 OneBot 11 标准。

            支持两种验证方式：
            1. Authorization header (Bearer token 或直接 token)
            2. X-Signature header (HMAC-SHA1 签名)
            """
            # 获取请求体（用于签名验证）
            body_bytes = await request.body()

            # 验证请求（如果配置了 secret）
            if self.secret_token:
                verified = False

                # 方式 1: 检查 X-Signature header (NapCat 默认使用此方式)
                if x_signature:
                    # NapCat 使用 HMAC-SHA1 签名
                    # 格式: sha1=<signature>
                    if x_signature.startswith("sha1="):
                        expected_signature = x_signature[5:]
                        # 计算 HMAC-SHA1
                        computed_signature = hmac.new(
                            self.secret_token.encode('utf-8'),
                            body_bytes,
                            hashlib.sha1
                        ).hexdigest()

                        if hmac.compare_digest(computed_signature, expected_signature):
                            verified = True
                            Logger.debug("WebhookServer", "Request verified via X-Signature")
                        else:
                            Logger.warn("WebhookServer",
                                       f"Invalid signature. Expected: {computed_signature}, Got: {expected_signature}")

                # 方式 2: 检查 Authorization header (兼容模式)
                elif authorization:
                    # 支持 Bearer token 或直接 token
                    if authorization.startswith("Bearer "):
                        token = authorization[7:]
                    else:
                        token = authorization

                    if token == self.secret_token:
                        verified = True
                        Logger.debug("WebhookServer", "Request verified via Authorization header")

                # 如果两种方式都没有通过验证
                if not verified:
                    Logger.warn("WebhookServer",
                               f"Authentication failed. X-Signature: {bool(x_signature)}, Authorization: {bool(authorization)}")
                    raise HTTPException(status_code=403, detail="Authentication failed")

            # 解析请求体
            try:
                data = await request.json()
            except Exception as e:
                Logger.error("WebhookServer", f"Failed to parse JSON: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON")

            # 记录接收到的事件类型
            post_type = data.get("post_type")
            Logger.debug("WebhookServer", f"Received event: post_type={post_type}")

            # 处理群消息事件
            if post_type == "message" and data.get("message_type") == "group":
                try:
                    message = GroupMessage.model_validate(data)
                    # 异步调用消息处理器，不阻塞响应
                    asyncio.create_task(self.message_handler(message))
                except Exception as e:
                    Logger.error("WebhookServer", f"Failed to process group message: {e}")
                    # 仍然返回 200，避免 NapCat 重试

            # 可以在此处添加其他事件类型的处理
            # elif post_type == "notice":
            #     ...
            # elif post_type == "request":
            #     ...

            # 返回成功响应
            return JSONResponse({"status": "ok"})

        @self.app.get("/health")
        async def health_check():
            """健康检查端点"""
            return {
                "status": "healthy",
                "service": "KiBot Webhook Server",
                "version": "2.0"
            }

        @self.app.get("/")
        async def root():
            """根路径"""
            return {
                "service": "KiBot Webhook Server",
                "message": "Webhook server is running. POST events to /webhook"
            }

        Logger.info("WebhookServer", "Routes registered: POST /webhook, GET /health, GET /")

    def get_app(self) -> FastAPI:
        """获取 FastAPI 应用实例"""
        return self.app
