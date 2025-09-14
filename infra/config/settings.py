from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env"
    )

    # NapCat 网络配置
    NAPCAT_WS: str = "ws://127.0.0.1:3001"
    NAPCAT_WS_AUTH_TOKEN: str = "<Token>"
    NAPCAT_HTTP: str = "http://127.0.0.1:3000"
    NAPCAT_HTTP_AUTH_TOKEN: str = "<Token>"

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


settings = Settings()
