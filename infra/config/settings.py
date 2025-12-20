from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    # 日志配置
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARN", "ERROR"] = "INFO"
    LOG_FILE: str = ""  # 日志文件路径，为空则不输出到文件

    # 连接模式: webhook 或 websocket
    CONNECTION_MODE: Literal["webhook", "websocket"] = "webhook"

    # NapCat 网络配置
    # WebSocket 配置
    NAPCAT_WS: str = "ws://127.0.0.1:3001"
    NAPCAT_WS_AUTH_TOKEN: str = "<Token>"

    # HTTP API 配置（用于调用 NapCat API）
    NAPCAT_HTTP: str = "http://127.0.0.1:3000"
    NAPCAT_HTTP_AUTH_TOKEN: str = "<Token>"

    # Webhook 配置（用于接收 NapCat 事件推送）
    NAPCAT_WEBHOOK_SECRET: str = ""  # Webhook 验证密钥，应与 NapCat 配置的 token 一致
    WEBHOOK_HOST: str = "0.0.0.0"    # Webhook 服务器监听地址
    WEBHOOK_PORT: int = 8000         # Webhook 服务器监听端口

    # LLM 相关配置
    LLM_BASE_URL: str = "<BASE_URL>"
    LLM_API_KEY: str = "<KEY>"
    LLM_MODEL: str = "<MODEL_NAME>"

    # 和风天气 API
    WEATHER_API_HOST: str = "<URL>"
    WEATHER_API_KEY: str = "<KEY>"

    # Embeddings API
    EMBEDDINGS_BASE_URL: str = "<BASE_URL>"
    EMBEDDINGS_API_KEY: str = "<KEY>"
    EMBEDDINGS_MODEL: str = "<MODEL_NAME>"

    # 联网搜索 API
    WEB_SEARCH_URL: str = "<URL>"
    WEB_SEARCH_API_KEY: str = "<KEY>"


settings = Settings()
