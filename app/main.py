# GoalAura_AI/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import os

# Import the core logic and models
from core.agent import generate_dynamic_roadmap
from core.comparison_agent import generate_comparison_insights
from core.models import DreamRoadmap, UserComparisonInsights

# --- 1. Define the Input Schema for the API ---
class DreamRequest(BaseModel):
    """Schema for the data sent from the mobile app to the API."""
    dream_text: str = Field(..., description="The user's natural language goal/dream.", example="I want to buy a Royal Enfield bike")
    estimated_budget: float = Field(..., gt=0, description="User's estimated budget for the dream in INR.", example=150000)
    user_monthly_income: float = Field(..., gt=0, description="The user's monthly income in INR.", example=50000)
    target_months: int = Field(..., gt=0, description="Number of months to achieve the dream.", example=12)


class ComparisonRequest(BaseModel):
    """Schema for user comparison analysis."""
    current_user_info: str = Field(..., description="Current user info in format: job_salary_savings", example="SoftwareEngineer_80000_50000")
    other_user_info: str = Field(..., description="Comparison user info in format: job_salary_savings", example="SoftwareEngineer_85000_65000")
    current_user_transactions: str = Field(..., description="Current user's transaction data in CSV format as string")
    other_user_transactions: str = Field(..., description="Comparison user's transaction data in CSV format as string")

# --- 2. Initialize FastAPI App ---
app = FastAPI(
    title="GoalAura AI Backend",
    description="Dynamic AI API for personalized dream roadmaps.",
    version="1.0.0"
)

# --- 3. Define the API Endpoint ---
@app.post("/api/dream-map", response_model=DreamRoadmap)
async def create_dream_map(request: DreamRequest):
    """
    Receives the user's dream with budget and timeline,
    returns brutally honest, realistic roadmap with detailed action plan.
    """
    try:
        # Call the enhanced AI logic
        roadmap = generate_dynamic_roadmap(
            dream_text=request.dream_text,
            estimated_budget=request.estimated_budget,
            user_income=request.user_monthly_income,
            target_months=request.target_months
        )

        # FastAPI automatically converts the Pydantic object to JSON
        return roadmap

    except Exception as e:
        print(f"Error processing dream map request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating the roadmap: {str(e)}"
        )


@app.post("/api/compare-users", response_model=UserComparisonInsights)
async def compare_users(request: ComparisonRequest):
    """
    Compares two users' financial profiles and transaction patterns.
    Returns personalized insights and recommendations for the current user.
    """
    try:
        # Call the comparison agent
        insights = generate_comparison_insights(
            current_user_info=request.current_user_info,
            other_user_info=request.other_user_info,
            current_user_transactions=request.current_user_transactions,
            other_user_transactions=request.other_user_transactions
        )
        
        return insights
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input format: {str(e)}"
        )
    except Exception as e:
        print(f"Error processing user comparison: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while comparing users: {str(e)}"
        )

# --- 4. Running the Server (for local testing/hackathon deployment) ---
if __name__ == "__main__":
    # Ensure environment variables are loaded if running this file directly
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the server on http://127.0.0.1:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)