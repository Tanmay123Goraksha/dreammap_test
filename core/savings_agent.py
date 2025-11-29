# core/savings_agent.py
import os
import json
from google import genai
from google.genai import types


# Initialize Gemini client only if key exists
client = None
if os.environ.get("GEMINI_API_KEY"):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def orchestrate_savings_plan(data: dict):
    """
    Core logic for generating 3 expert-level savings plans:
    - Minimal Plan
    - Balanced Plan
    - Premium Plan

    Returns structured JSON for the API endpoint.
    """

    if not client:
        raise RuntimeError("GEMINI_API_KEY missing. Savings planner cannot run.")

    # -----------------------------------------------
    # SYSTEM INSTRUCTION (FINANCIAL ADVISOR ROLE)
    # -----------------------------------------------
    system_instruction = (
        "You are a world-class Indian financial advisor. Your expertise includes: "
        "budget optimization, household cashflow analysis, SIP planning, index funds, "
        "gold vs equity balancing, long-term retirement strategy, inflation-adjusted "
        "wealth planning, and behavioural finance. You create structured financial "
        "plans with high clarity and realism, suitable for users with low financial knowledge."
    )

    # -----------------------------------------------
    # PROMPT CONSTRUCTION
    # -----------------------------------------------
    prompt = f"""
User Financial Data:
- Monthly Income: ₹{data["monthly_income"]}
- Fixed Expenses: ₹{data["fixed_expenses"]}
- Variable Expenses: ₹{data["variable_expenses"]}
- Number of Dependents: {data["number_of_dependents"]}
- EMI Obligations: ₹{data["emi_obligations"]}
- Current Savings: ₹{data["current_savings"]}
- Risk Profile: {data["risk_profile"]}
- Lifestyle Preference: {data["lifestyle_preference"]}
- Savings Goal: {data["savings_goal"]}

TASK:
Create a savings & investment plan with **three distinct difficulty levels**:

1. **Minimalism Plan (High Discipline, Maximum Savings)**
2. **Balanced Plan (Moderate Lifestyle + Strong Investments)**
3. **Premium Plan (Higher Lifestyle Comfort Without Compromising Future Stability)**

For each plan, include ALL of the following:

- Monthly Budget Breakdown (₹ values + percentages)
- Recommended Investment Allocation (SIP, Index Funds, Gold, Bonds, PPF)
- Luxury Spending Limit (₹)
- Emergency Fund Strategy
- Risk Adjusted Advice
- High-level 12-month projection
- Psychological guidance (behavioural finance insights)

Return the output STRICTLY in this JSON format:

{{
  "minimal_plan": {{
    "monthly_budget": {{}},
    "investment_allocation": {{}},
    "luxury_limit_inr": 0,
    "emergency_fund_plan": "string",
    "advisor_notes": "string",
    "projection_12_months": "string"
  }},
  "balanced_plan": {{
    "monthly_budget": {{}},
    "investment_allocation": {{}},
    "luxury_limit_inr": 0,
    "emergency_fund_plan": "string",
    "advisor_notes": "string",
    "projection_12_months": "string"
  }},
  "premium_plan": {{
    "monthly_budget": {{}},
    "investment_allocation": {{}},
    "luxury_limit_inr": 0,
    "emergency_fund_plan": "string",
    "advisor_notes": "string",
    "projection_12_months": "string"
  }}
}}
"""

    # -----------------------------------------------
    # GEMINI CALL (single call)
    # -----------------------------------------------
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)
