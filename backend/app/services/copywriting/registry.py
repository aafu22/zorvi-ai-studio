from app.core.errors import AppError
from app.services.copywriting.base import CopyProvider
from app.services.copywriting.rule_based import RuleBasedProvider

_PROVIDERS: dict[str, CopyProvider] = {
    "template": RuleBasedProvider(),
    # "llm": MyLlmProvider(api_key=get_settings().llm_api_key),  # future, see base.py
}


def get_provider(provider_id: str) -> CopyProvider:
    provider = _PROVIDERS.get(provider_id)
    if provider is None:
        raise AppError(400, f"Unknown copy provider: {provider_id}")
    return provider
