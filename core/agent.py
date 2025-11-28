import os
import json
import re
from typing import Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from core.models import DreamRoadmap
from tools.financial_tools import get_real_world_cost, parse_price_inr,calculate_opportunity_cost

load_dotenv()

# Define the tool declaration expected by Gemini
get_real_world_cost_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_real_world_cost",
            description="Finds the estimated real-world cost for a specific item based on a search query and location, in INR.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "item_query": types.Schema(type=types.Type.STRING, description="The item or service to find the cost for."),
                    "location": types.Schema(type=types.Type.STRING, description="The location for the cost estimate.")
                },
                required=["item_query"]
            )
        )
    ]
)

# Initialize client (safe guard in case key missing)
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    client = None
    print(f"Warning: Gemini client init failed: {e}")

def _safe_generate_content(*, model: str, contents, config):
    """
    Wrap model call to provide clearer errors when client is not initialized.
    """
    if client is None:
        raise RuntimeError("GenAI client not initialized. Set GEMINI_API_KEY in env.")
    return client.models.generate_content(model=model, contents=contents, config=config)

# at top of core/agent.py add:
from tools.cost_engine import classify_dream, estimate_total_cost_with_ai, build_breakdown_from_template

def generate_dynamic_roadmap(dream_text: str, user_income: float, target_months: int | None = None) -> DreamRoadmap:
    """
    Dynamic AI processing: Extract dream category, estimate cost using real-world tool, calculate timeline,
    generate milestones. Lightweight, token-efficient, no templates.
    """
    model_name = "gemini-2.5-pro"

    if not os.environ.get("GEMINI_API_KEY"):
        # Fail-safe: Return fallback if API unavailable
        return DreamRoadmap(
            dreamType="unknown",
            estimatedCost=0,
            months=0,
            monthlySaving=0,
            savingPercentage=0.0,
            milestones=["AI unavailable — fallback activated"]
        )

    # --- STEP 1: Classify dream and get real-world cost ---
    dream_type, _ = classify_dream(dream_text)
    cost_response = get_real_world_cost(dream_text, "Mumbai, India")
    estimated_cost = parse_price_inr(cost_response)
    if estimated_cost <= 0:
        estimated_cost = 100000  # fallback

    # Use target_months if provided, else default
    months = target_months if target_months else 12
    if months <= 0:
        months = 12

    # Calculate monthly saving and percentage
    monthly_saving = round(estimated_cost / months, 2)
    saving_percentage = round((monthly_saving / user_income) * 100, 2) if user_income > 0 else 0.0

    # --- STEP 2: Generate milestones with AI ---
    prompt = (
        f"Dream: '{dream_text}'. Category: {dream_type}. "
        f"Estimated cost: ₹{estimated_cost}. Timeline: {months} months. "
        "Generate 5-7 concise milestones for achieving this dream with cost if required. "
        "Return only a JSON array of strings, e.g., [\"milestone1\", \"milestone2\", ...]."
    )

    try:
        response = _safe_generate_content(
            model=model_name,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        milestones = json.loads(response.text)
        if not isinstance(milestones, list) or len(milestones) < 5:
            milestones = [f"Step {i+1}" for i in range(7)]
    except Exception as e:
        print(f"Milestone generation failed: {e}")
        milestones = [f"Step {i+1}" for i in range(7)]

    return DreamRoadmap(
        dreamType=dream_type,
        estimatedCost=estimated_cost,
        months=months,
        monthlySaving=monthly_saving,
        savingPercentage=saving_percentage,
        milestones=milestones[:7]
    )




def orchestrate_opportunity_cost(purchase_item: str,purchase_cost: float, user_hourly_wage: float) -> str:
    """
    Runs the Opportunity Cost Visualizer agent: calculates costs and generates the message.
    """
    print("\n--- Agent Step: Calculating Opportunity Cost ---")
    
    # 1. Call the Tool Directly (Internal Calculation)
    tool_output_json = calculate_opportunity_cost(purchase_cost, user_hourly_wage)
    tool_output = json.loads(tool_output_json)
    
    if "error" in tool_output:
        return f"Error: {tool_output['error']}"

    # 2. Format the Output using Gemini Flash for emotionally intelligent phrasing
    
    system_instruction = (
    "You are GoalAura's proactive Behavioral Financial Advisor. Your task is to analyze a user's impulse purchase "
    "using the provided opportunity cost data and deliver a structured, non-judgmental intervention message. "
    "Your response must include four sections clearly marked with headings."

    )
    
    # Ensure correct formatting for the prompt
    prompt = (
        f"USER PURCHASE ANALYSIS: "
        f"Item: {purchase_item} (Cost: ₹{purchase_cost:,.0f}). "
        f"Time Cost: {tool_output['time_cost_hours']} hours of work. "
        f"Investment Future Value: ₹{tool_output['future_value_inr']:,.0f} in {tool_output['investment_years']} years. "
        
        "\n\n**TASK: Generate a persuasive and structured response with the following four sections:**"
        "\n\n## 1. Quick Assessment (Good or Bad Purchase?)"
        "**Analyze:** Based on standard financial principles (is this a depreciating consumption asset vs. appreciating or necessary asset?). State whether it's financially 'Good' or 'Bad' and explain why briefly."
        
        "\n\n## 2. The Cost of Time and Future"
        "Use the calculated values to deliver the time cost and future value message precisely, formatted as requested by the user: 'This [Cost] equals [Time] OR could become [Future Value] in 5 years.'"
        
        "\n\n## 3. Better Alternatives"
        "Suggest 2-3 specific financial or experiential alternatives that provide a similar emotional benefit (e.g., 'If it's for joy, put 10% toward a weekend trip' or 'If it's for status, invest in a quality course')."
        
        "\n\n## 4. Delayed Gratification Challenge"
        "Conclude with a specific, actionable challenge (e.g., 'Wait 72 hours and move 50% of the cost into your GoalAura savings account for now')."
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-pro", # Faster model for quick response
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
        config=types.GenerateContentConfig(system_instruction=system_instruction)
    )
    
    return response.text
