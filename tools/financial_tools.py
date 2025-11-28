import re

def _extract_first_numeric_rupee(text: str) -> float:
    text = text.replace(",", "")
    m = re.search(r"₹\s*([0-9]+(?:\.[0-9]+)?)", text)
    if m:
        return float(m.group(1))

    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(crore|cr)", text, re.I)
    if m:
        return float(m.group(1)) * 10_000_00

    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(lakh|lac|l)", text, re.I)
    if m:
        return float(m.group(1)) * 1_00_000

    nums = re.findall(r"[0-9]{4,}", text)
    if nums:
        return float(max(map(int, nums)))

    return -1.0


# GoalAura_AI/tools/financial_tools.py (Ensure structured output)

def get_real_world_cost(item_query: str, location: str = "Mumbai, India") -> str:
    """
    Finds detailed cost components and returns a JSON string for the AI to process.
    The AI will calculate the total cost from this list.
    """
    # *** HACKATHON SIMULATION LOGIC: RETURNING STRUCTURED DATA ***
    if "bakery" in item_query.lower():
        cost_data = [
            {"item": "Commercial Oven (1 deck)", "type": "Equipment", "cost_inr": 120000},
            {"item": "Monthly Rent Deposit (3 months)", "type": "Initial Fixed", "cost_inr": 150000},
            {"item": "Initial Ingredient Stock", "type": "Startup", "cost_inr": 30000},
            {"item": "Monthly Utility Estimate", "type": "Recurring Monthly", "cost_inr": 10000}
        ]
    # ... (other cost data examples) ...
    else:
        cost_data = [{"item": item_query, "type": "One-time", "cost_inr": 85000}]
    
    return json.dumps(cost_data)


def parse_price_inr(text: str) -> float:
    return _extract_first_numeric_rupee(text)




# GoalAura_AI/tools/financial_tools.py (ADD THIS NEW FUNCTION)
import json
import math

# --- Constants for Opportunity Cost ---
ASSUMED_ANNUAL_RETURN_RATE = 0.10  # 10% (r)
INVESTMENT_PERIOD_YEARS = 5       # 5 years (n)
# -------------------------------------

def calculate_opportunity_cost(
    purchase_cost: float, 
    user_hourly_wage: float
) -> str:
    """
    Calculates the hours of work required for a purchase and its future value if invested.
    Returns a structured JSON string summarizing the two costs for the AI to present.
    """
    
    # 1. Calculate Hours of Work (Time Cost)
    if user_hourly_wage <= 0:
        return json.dumps({"error": "Hourly wage must be greater than zero."})
        
    hours_of_work = purchase_cost / user_hourly_wage

    # 2. Calculate Future Value (Investment Cost)
    # Formula: FV = PV * (1 + r)^n
    future_value = purchase_cost * (
        (1 + ASSUMED_ANNUAL_RETURN_RATE) ** INVESTMENT_PERIOD_YEARS
    )
    
    # Rounding the results for the visualization
    formatted_hours = round(hours_of_work, 1)
    formatted_fv = round(future_value, 0) # Round to nearest rupee

    # Return the structured data as a JSON string
    return json.dumps({
        "time_cost_hours": formatted_hours,
        "future_value_inr": formatted_fv,
        "investment_years": INVESTMENT_PERIOD_YEARS
    })