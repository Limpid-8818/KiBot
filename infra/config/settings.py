from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    # NapCat 网络配置
    NAPCAT_WS: str = "ws://127.0.0.1:3001"
    NAPCAT_HTTP: str = "http://127.0.0.1:3000"

    # LLM 相关配置
    LLM_BASE_URL: str = "<BASE_URL>"
    LLM_API_KEY: str = "<KEY>"
    LLM_MODEL: str = "<MODEL_NAME>"
