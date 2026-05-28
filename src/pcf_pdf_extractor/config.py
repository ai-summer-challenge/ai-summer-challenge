from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    company_api_base_url: AnyHttpUrl | None = None
    company_api_token: SecretStr | None = None
    company_api_timeout_seconds: float = Field(default=30.0, gt=0)

    llm_api_base_url: AnyHttpUrl | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_input_chars: int = Field(default=269_000, gt=0)

    reference_bafu_extract_path: Path = Path("resources/BAFU Extract.xlsx")
    reference_oil_gas_eclasses_path: Path = Path(
        "resources/EclasseswithOilGasRelevance.txt"
    )
    reference_mapping_prompt_path: Path = Path("resources/prompt_mapping.txt")
    reference_mapping_candidate_limit: int = Field(default=120, gt=0)
    extraction_system_prompt_path: Path = Path("resources/extraction_system_prompt.txt")
    extraction_user_prompt_path: Path = Path("resources/extraction_user_prompt.txt")


@lru_cache
def get_settings() -> Settings:
    return Settings()
