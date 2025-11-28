# GoalAura_AI/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import os

# Import the core logic and models
from core.agent import generate_dynamic_roadmap
from core.models import DreamRoadmap

# --- 1. Define the Input Schema for the API ---
class DreamRequest(BaseModel):
    """Schema for the data sent from the mobile app to the API."""
    dream_text: str = Field(..., description="The user's natural language goal/dream.", example="I want to buy a bike and start within 12 months.")
    user_monthly_income: float = Field(..., gt=0, description="The user's monthly income in INR.", example=50000)
    target_months: int | None = Field(None, gt=0, description="Optional: number of months the user wants to achieve the dream.", example=12)

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
    Receives the user's dream, runs dynamic AI processing,
    and returns the lightweight roadmap.
    """
    try:
        # Call the dynamic AI logic
        roadmap = generate_dynamic_roadmap(
            dream_text=request.dream_text,
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

# --- 4. Running the Server (for local testing/hackathon deployment) ---
if __name__ == "__main__":
    # Ensure environment variables are loaded if running this file directly
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the server on http://127.0.0.1:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)