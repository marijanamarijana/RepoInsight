from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and `.env`.

    Put secrets (GitHub token) in `.env` — that file is gitignored.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    github_token: str = ""
    github_api_base: str = "https://api.github.com"
    max_pages_default: int = 5
    request_timeout: int = 30

    ai_provider: str = "ollama"
    ai_model: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_request_timeout: int = 600
    ai_max_tokens: int = 2000
    ai_request_timeout: int = 180
    ai_compact_context: bool = True


settings = Settings()
