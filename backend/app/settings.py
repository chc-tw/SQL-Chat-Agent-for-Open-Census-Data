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

class OpenAISettings(BaseSettings):
    api_key: str = Field(default=...)
    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=str(ENV_FILE),
        case_sensitive=False,
        extra="ignore",
    )

class AuthSettings(BaseSettings):
    jwt_secret: str = Field(default="dev-secret-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)
    users: str = Field(default='[{"username":"admin","password":"admin"}]')

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        case_sensitive=False,
        extra="ignore",
    )


class FirestoreSettings(BaseSettings):
    project_id: str = Field(default="chc-snowflake-agent")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_prefix="GCP_",
        case_sensitive=False,
        extra="ignore",
    )


# All settings
snowflake_settings = SnowflakeSettings()
anthropic_settings = AnthropicSettings()
openai_settings = OpenAISettings()
auth_settings = AuthSettings()
firestore_settings = FirestoreSettings()
