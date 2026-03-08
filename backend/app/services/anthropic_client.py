from anthropic import Anthropic, AsyncAnthropic

from app.settings import anthropic_settings

client = AsyncAnthropic(api_key=anthropic_settings.api_key)
sync_client = Anthropic(api_key=anthropic_settings.api_key)
