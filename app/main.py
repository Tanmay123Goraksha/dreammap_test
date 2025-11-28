# GoalAura_AI/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import os

# Import the core logic and models
from core.agent import generate_dynamic_roadmap, orchestrate_opportunity_cost
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




# --- New Input Schema ---
class PurchaseRequest(BaseModel):
    """Schema for a purchase decision."""
    purchase_item: str = Field(..., description="The name or description of the item being considered for purchase.", example="iPhone 15")
    purchase_cost_inr: float = Field(..., gt=0, description="Cost of the item being considered.")
    user_monthly_income: float = Field(..., gt=0, description="User's current monthly income in INR.")

# --- New Endpoint for Opportunity Cost ---
# Add this endpoint below the existing create_dream_map function
@app.post("/api/opportunity-cost")
async def get_opportunity_cost(request: PurchaseRequest):
    """
    Calculates the opportunity cost (time vs. investment) for an impulse purchase.
    """
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=500, 
                detail="Server error: GEMINI_API_KEY not configured."
            )
            
        # 1. Calculate Hourly Wage (Assuming 20 working days * 8 hours = 160 hours/month)
        # This makes the feature instantly personalized.
        HOURS_PER_MONTH = 160.0
        hourly_wage = request.user_monthly_income / HOURS_PER_MONTH
        
        # 2. Call the dedicated Agent function
        visualizer_text = orchestrate_opportunity_cost(
            purchase_item=request.purchase_item,
            purchase_cost=request.purchase_cost_inr,
            user_hourly_wage=hourly_wage
        )
        
        return {"visualizer_message": visualizer_text}

    except Exception as e:
        print(f"Error processing opportunity cost request: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while calculating opportunity cost: {str(e)}"
        )












# --- 4. Running the Server (for local testing/hackathon deployment) ---
if __name__ == "__main__":
    # Ensure environment variables are loaded if running this file directly
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the server on http://127.0.0.1:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)