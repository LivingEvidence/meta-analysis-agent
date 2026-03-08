from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    RUNS_DIR: Path = Path("./runs")
    UPLOADS_DIR: Path = Path("./uploads")
    SKILLS_DIR: Path = Path("./skills")
    DOCKER_IMAGE_NAME: str = "meta-analysis-r"
    DOCKER_BUILD_CONTEXT: Path = Path("./skills/meta-analysis/scripts/docker")
    R_SCRIPTS_DIR: Path = Path("./skills/meta-analysis/scripts/R")
    MAX_AGENT_TURNS: int = 25
    AGENT_MODEL: str = "sonnet"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
