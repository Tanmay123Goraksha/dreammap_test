from pydantic import BaseModel, Field
from typing import List

class DreamRoadmap(BaseModel):
    """Lightweight, dynamic roadmap response."""
    dreamType: str = Field(description="Category of the dream (e.g., bike, phone, home renovation).")
    estimatedCost: float = Field(description="Realistic cost estimate in INR for India.")
    months: int = Field(description="Timeline in months (user-provided or calculated).")
    monthlySaving: float = Field(description="Exact monthly savings = estimatedCost / months.")
    savingPercentage: float = Field(description="Percentage of monthly income needed for savings.")
    milestones: List[str] = Field(description="5-7 custom milestones based on the dream.")
