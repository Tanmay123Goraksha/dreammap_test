# GoalAura_AI/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import os

# Import the core logic and models
from core.agent import orchestrate_dream_mapping
from core.models import FinancialRoadmap

# --- 1. Define the Input Schema for the API ---
class DreamRequest(BaseModel):
    """Schema for the data sent from the mobile app to the API."""
    dream_text: str = Field(..., description="The user's natural language goal/dream.")
    user_monthly_income: float = Field(..., gt=0, description="The user's monthly income in INR.")

# --- 2. Initialize FastAPI App ---
app = FastAPI(
    title="GoalAura AI Backend",
    description="Agentic AI API for Dream Mapping and Reverse Budget Engineering.",
    version="1.0.0"
)

# --- 3. Define the API Endpoint ---
@app.post("/api/dream-map", response_model=FinancialRoadmap)
async def create_dream_map(request: DreamRequest):
    """
    Receives the user's dream and income, runs the Agentic AI, 
    and returns the structured financial roadmap.
    """
    try:
        # Check for API Key before running the agent
        if not os.environ.get("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=500, 
                detail="Server error: GEMINI_API_KEY not configured."
            )

        # Call the core Agentic AI logic
        roadmap = orchestrate_dream_mapping(
            dream_text=request.dream_text, 
            user_income=request.user_monthly_income
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