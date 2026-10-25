from typing import Protocol

from app.schemas.copy import CopyRequest, CopyResponse, ProviderInfo


class CopyProvider(Protocol):
    """Interface every copy generator implements.

    To add an LLM later: create a class with these members (set is_ai = True), call your
    API inside generate(), map the result into CopyResponse, then register it in
    registry.py when its API key is configured. Routes and UI need no changes: the UI
    reads `provider.is_ai` from the response to label the output honestly.
    """

    id: str
    label: str
    is_ai: bool

    def generate(self, request: CopyRequest) -> CopyResponse: ...


def provider_info(provider: CopyProvider) -> ProviderInfo:
    return ProviderInfo(id=provider.id, label=provider.label, is_ai=provider.is_ai)
