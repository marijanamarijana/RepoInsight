from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    github_token: str = ""
    github_api_base: str = "https://api.github.com"
    max_pages_default: int = 5
    request_timeout: int = 30


settings = Settings()
