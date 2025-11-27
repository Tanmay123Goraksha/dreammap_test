# GoalAura_AI/core/models.py
from pydantic import BaseModel, Field
from typing import Literal

class FinancialGoal(BaseModel):
    """Structured data for a user's financial dream/goal, output by the AI."""
    goal_name: str = Field(description="A concise title for the user's dream.")
    description_summary: str = Field(description="A brief summary of the dream.")
    estimated_primary_cost_item: str = Field(description="The main item or service that costs the most (e.g., 'commercial oven', 'down payment').")
    cost_uncertainty_level: Literal["Low", "Medium", "High"] = Field(description="How uncertain the final cost is, based on the user's description.")
    user_timeline_preference: Literal["Aggressive", "Comfortable", "Luxury"] = Field(description="The preferred pace for achieving the goal.")

class RoadmapOption(BaseModel):
    """A single timeline option within the financial plan."""
    path_name: str = Field(description="Name of the path (e.g., Aggressive, Comfortable, Luxury).")
    duration_months: int = Field(description="Total months to achieve the goal.")
    monthly_savings_required: float = Field(description="The required savings amount per month (in INR).")
    savings_as_percentage_of_income: float = Field(description="Monthly savings required as a percentage of the user's income.")

class FinancialRoadmap(BaseModel):
    """The final structured output containing the full plan."""
    total_estimated_budget_inr: float = Field(description="The final total budget calculated for the goal.")
    milestone_summary: str = Field(description="A brief narrative summary of the key steps.")
    timeline_options: list[RoadmapOption]