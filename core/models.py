# GoalAura_AI/core/models.py (Snippet)

from pydantic import BaseModel, Field
from typing import List, Optional

# Final Output Schema
class DreamRoadmap(BaseModel):
    """Enhanced roadmap with realistic, brutally honest guidance."""
    dreamType: str = Field(description="Category of the dream (e.g., bike, phone, home renovation).")
    isRealistic: bool = Field(description="Whether the dream is achievable with given budget and timeline.")
    realityCheck: str = Field(description="Brutally honest assessment of the dream's feasibility.")
    estimatedCost: float = Field(description="Realistic market cost estimate in INR.")
    userBudget: float = Field(description="User's stated budget.")
    budgetGap: float = Field(description="Difference between estimated cost and user budget.")
    months: int = Field(description="Timeline in months.")
    monthlySaving: float = Field(description="Required monthly savings.")
    savingPercentage: float = Field(description="Percentage of monthly income needed.")
    feasibilityScore: int = Field(description="Score from 1-10 indicating how achievable this is.")
    actionPlan: List[str] = Field(description="Detailed, realistic step-by-step action plan (7-10 steps).")
    challenges: List[str] = Field(description="Real-world challenges and obstacles to expect.")
    alternatives: Optional[List[str]] = Field(default=None, description="Alternative approaches if dream is unrealistic.")
    proTips: List[str] = Field(description="Practical tips and insider knowledge for achieving this goal.")


class UserComparisonInsights(BaseModel):
    """Response model for user comparison analysis."""
    summary: str = Field(description="Brief summary comparing both users' financial profiles.")
    job_comparison: str = Field(description="Insights about job profiles and income patterns.")
    savings_insights: str = Field(description="Comparison of savings patterns and strategies.")
    spending_patterns: List[str] = Field(description="Key differences in spending behavior.")
    recommendations: List[str] = Field(description="Personalized recommendations for the current user.")
    unnecessary_expenses: List[str] = Field(description="Identified unnecessary transactions to avoid.")
    peer_benchmark: str = Field(description="Benchmark insight comparing to similar profiles.")
