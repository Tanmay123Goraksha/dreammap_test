# GoalAura_AI/core/models.py (Snippet)

from pydantic import BaseModel, Field
from typing import List

# Final Output Schema
class DreamRoadmap(BaseModel):
    """The final structured roadmap."""
    dream_type: str = Field(description="The category of the dream (e.g., 'Business Startup', 'Major Purchase').")
    total_cost_inr: float = Field(description="The total estimated startup capital required, calculated by the AI.")
    milestones: List[str] = Field(description="5-7 concise, actionable steps for the user.")
    monthly_saving: float = Field(description="Required monthly savings to hit the total cost in the target duration.")
    saving_percentage: float = Field(description="Monthly savings required as a percentage of user's income.")