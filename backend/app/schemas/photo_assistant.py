from pydantic import BaseModel, Field


class PhotoAnalysis(BaseModel):
    product_type: str = Field(description="Likely product category, with uncertainty noted when needed")
    visible_features: list[str] = Field(description="Only details visibly supported by the photo")
    product_title: str
    visual_description: str
    background_suggestions: list[str]
    composition_suggestions: list[str]
    lighting_recommendations: list[str]
    framing_recommendations: list[str]
    color_palette: list[str]
    confidence_note: str
