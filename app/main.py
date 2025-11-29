# GoalAura_AI/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import os

# Import the core logic and models
# GoalAura_AI/app/main.py (CORRECTED IMPORT)
from core.agent import orchestrate_dream_roadmap, orchestrate_opportunity_cost
from core.savings_agent import orchestrate_savings_plan
from core.models import DreamRoadmap
from google import genai
from google.genai import types
import json
from typing import Optional, List, Dict, Any


if os.environ.get("GEMINI_API_KEY"):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
else:
    client = None


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
        roadmap = orchestrate_dream_roadmap(
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





class QuantumDecisionRequest(BaseModel):
    """Schema for Quantum Decision Tree evaluation."""
    situation: str = Field(
        ...,
        description="A natural language description of the decision or dilemma.",
        example="Should I buy a gaming laptop or save the money for relocation?"
    )
    user_monthly_income: float = Field(
        ...,
        gt=0,
        description="User's monthly income in INR."
    )
    user_savings_inr: float = Field(
        ...,
        ge=0,
        description="User's current savings."
    )
    risk_profile: str = Field(
        ..., 
        description="User's risk preference: low, medium, or high.",
        example="medium"
    )


@app.post("/api/quantum-decision-tree")
async def quantum_decision_tree(request: QuantumDecisionRequest):
    """
    Evaluates a user's dilemma using a Quantum Decision Tree (QDT) model.
    Uses a single Gemini call and behaves like a professional financial advisor.
    """
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="Server error: GEMINI_API_KEY not configured."
            )

        # --- Construct the QDT Prompt ---
        system_instruction = (
            "You are GoalAura's Quantum Decision Tree Engine: a professional "
            "financial advisor trained in behavioral psychology, risk modeling, "
            "loss-aversion theory, decision science, and long-term planning. "
            "Your job is to evaluate dilemmas and output a structured recommendation."
        )

        prompt = f"""
User Situation: {request.situation}
Monthly Income: ₹{request.user_monthly_income:,.0f}
Current Savings: ₹{request.user_savings_inr:,.0f}
Risk Profile: {request.risk_profile}

TASK:
Evaluate the scenario using a Quantum Decision Tree (QDT), where each branch
represents a probabilistic mental model:

1. Immediate Gratification Path
2. Delayed Gratification Path
3. Risk-Averse Conservative Path
4. High-Utility Strategic Path

Return the output strictly in this JSON structure:

{{
  "decision_rating": "Smart | Neutral | Risky",
  "recommended_choice": "string",
  "confidence_score": 0-100,
  "reasoning": {{
    "financial_factors": "string",
    "psychological_factors": "string",
    "opportunity_cost_view": "string",
    "risk_analysis": "string"
  }},
  "quantum_paths": [
    {{
      "path_name": "Immediate Gratification",
      "outcome": "string",
      "probability": "percentage"
    }},
    {{
      "path_name": "Delayed Gratification",
      "outcome": "string",
      "probability": "percentage"
    }},
    {{
      "path_name": "Conservative Path",
      "outcome": "string",
      "probability": "percentage"
    }},
    {{
      "path_name": "Strategic Path",
      "outcome": "string",
      "probability": "percentage"
    }}
  ],
  "final_advice": "string"
}}
        """

        # --- GEMINI CALL (Only One Call) ---
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )


        result = json.loads(response.text)
        return result

    except Exception as e:
        print(f"QDT error: {e}")
        raise HTTPException(status_code=500, detail=f"QDT processing error: {str(e)}")




# ============================================================
# SAVINGS & INVESTMENT PLANNER ENDPOINT
# ============================================================

class SavingsRequest(BaseModel):
    """User provides full financial profile for custom savings planning."""
    monthly_income: float = Field(..., gt=0, example=50000)
    fixed_expenses: float = Field(..., ge=0, example=20000)
    variable_expenses: float = Field(..., ge=0, example=10000)
    number_of_dependents: int = Field(..., ge=0, example=2)
    savings_goal: str = Field(..., example="Build a ₹5 lakh emergency fund and start investing")
    risk_profile: str = Field(..., example="medium")  # low | medium | high
    current_savings: float = Field(..., ge=0, example=30000)
    emi_obligations: float = Field(0, ge=0, example=5000)
    lifestyle_preference: str = Field(
        "balanced",
        description="minimal | balanced | premium",
        example="balanced"
    )



@app.post("/api/savings-advisor")
async def savings_advisor(request: SavingsRequest):
    try:
        result = orchestrate_savings_plan(request.dict())
        return result
    except Exception as e:
        print("Savings Advisor Error →", e)
        raise HTTPException(500, f"Savings planner failed: {str(e)}")



# import the agent at top of main.py
from core.lifestyle_agent import orchestrate_lifestyle_projection

# Pydantic request model (add near other models)
class LifestyleRequest(BaseModel):
    monthly_income: float = Field(..., gt=0)
    fixed_expenses: float = Field(..., ge=0)
    variable_expenses: float = Field(..., ge=0)
    emi_obligations: float = Field(0, ge=0)
    current_savings: float = Field(0, ge=0)
    number_of_dependents: int = Field(0, ge=0)
    risk_profile: str = Field("medium")
    city_tier: Optional[int] = Field(None, description="1=metro,2=city,3=tier-2 (optional)")
    goals: Optional[List[Dict[str, Any]]] = Field(None, description="Optional list of goals: [{name, target, deadline_months}]")

@app.post("/api/lifestyle-projection")
async def lifestyle_projection_endpoint(req: LifestyleRequest):
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

        payload = req.dict()
        result = orchestrate_lifestyle_projection(payload, model_name="gemini-2.5-pro")
        return result
    except Exception as e:
        print(f"Lifestyle projection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))






# --- 4. Running the Server (for local testing/hackathon deployment) ---
if __name__ == "__main__":
    # Ensure environment variables are loaded if running this file directly
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the server on http://127.0.0.1:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)