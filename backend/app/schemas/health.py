from pydantic import BaseModel


class Capabilities(BaseModel):
    llm_provider: bool


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    capabilities: Capabilities
