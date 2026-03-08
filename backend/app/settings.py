# %%
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"


class SnowflakeSettings(BaseSettings):
    account: str = Field(default=...)
    user: str = Field(default=...)
    password: str = Field(default=...)
    warehouse: str = Field(default=...)
    database: str = Field(default=...)
    db_schema: str = Field(
        default=..., validation_alias="snowflake_schema", serialization_alias="schema"
    )

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_prefix="SNOWFLAKE_",
        case_sensitive=False,
        # 額外保險：允許使用 alias 名稱來初始化物件
        populate_by_name=True,
        extra="ignore",
    )


class AnthropicSettings(BaseSettings):
    api_key: str = Field(default=...)
    model_config = SettingsConfigDict(
        env_prefix="ANTHROPIC_",
        env_file=str(ENV_FILE),
        case_sensitive=False,
        extra="ignore",
    )


# All settings
snowflake_settings = SnowflakeSettings()
anthropic_settings = AnthropicSettings()
