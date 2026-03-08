from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    CLAUDE_CODE_USE_FOUNDRY: bool = False
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_FOUNDRY_API_KEY: str = ""
    ANTHROPIC_FOUNDRY_RESOURCE: str = ""
    ANTHROPIC_DEFAULT_SONNET_MODEL: str = ""
    ANTHROPIC_DEFAULT_HAIKU_MODEL: str = ""
    ANTHROPIC_DEFAULT_OPUS_MODEL: str = ""
    RUNS_DIR: Path = Path("./runs")
    UPLOADS_DIR: Path = Path("./uploads")
    SKILLS_DIR: Path = Path("./skills")
    DOCKER_IMAGE_NAME: str = "meta-analysis-r"
    DOCKER_BUILD_CONTEXT: Path = Path("./skills/meta-analysis/scripts/docker")
    R_SCRIPTS_DIR: Path = Path("./skills/meta-analysis/scripts/R")
    MAX_AGENT_TURNS: int = 25
    AGENT_MODEL: str = "sonnet"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
