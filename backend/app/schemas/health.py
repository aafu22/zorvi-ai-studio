from pydantic import BaseModel


class Capabilities(BaseModel):
    llm_provider: bool
    background_removal: bool


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    capabilities: Capabilities
