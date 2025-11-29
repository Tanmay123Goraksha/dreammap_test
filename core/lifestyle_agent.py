# core/lifestyle_agent.py
import os
import json
import math
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Gemini imports
from google import genai
from google.genai import types

load_dotenv()

# init client (safe)
client = None
if os.environ.get("GEMINI_API_KEY"):
    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    except Exception as e:
        client = None
        print(f"Warning: Gemini init failed in lifestyle_agent: {e}")

# ----------------------------
# Local deterministic math
# ----------------------------

def _growth_rate_by_risk(risk_profile: str) -> float:
    # user-specified mapping: low:6%, medium:8.5%, high:11%
    r = risk_profile.lower() if isinstance(risk_profile, str) else "medium"
    return {"low": 0.06, "medium": 0.085, "high": 0.11}.get(r, 0.085)

def _coli_by_city_tier(city_tier: Optional[int]) -> float:
    # optional city-tier override: None->use default 6.5%
    if city_tier == 1:
        return 0.07
    if city_tier == 2:
        return 0.06
    if city_tier == 3:
        return 0.05
    return 0.065

def project_value(amount: float, annual_rate: float, years: float) -> float:
    return amount * ((1 + annual_rate) ** years)

def months_to_reach(goal_amount: float, monthly_saved: float) -> int:
    if monthly_saved <= 0:
        return 10**6
    return math.ceil(goal_amount / monthly_saved)

def compute_financial_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    # normalize inputs
    income = float(payload.get("monthly_income", 0))
    fixed = float(payload.get("fixed_expenses", 0))
    variable = float(payload.get("variable_expenses", 0))
    emi = float(payload.get("emi_obligations", 0))
    current_savings = float(payload.get("current_savings", 0))
    dependents = int(payload.get("number_of_dependents", 0))
    risk_profile = payload.get("risk_profile", "medium")
    city_tier = payload.get("city_tier", None)  # optional

    disposable = max(0.0, income - fixed - emi - variable)
    savings_rate = 0.0
    if income > 0:
        savings_rate = round((max(0.0, income - fixed - variable - emi) / income) * 100, 2)

    # emergency recommended (3 months of needs)
    monthly_needs = fixed + variable
    emergency_recommended = monthly_needs * 3

    growth_rate = _growth_rate_by_risk(risk_profile)
    coli = _coli_by_city_tier(city_tier)

    # projections
    income_6m = project_value(income, growth_rate, 0.5)
    income_12m = project_value(income, growth_rate, 1.0)
    income_36m = project_value(income, growth_rate, 3.0)

    expenses_6m = project_value(monthly_needs, coli, 0.5)
    expenses_12m = project_value(monthly_needs, coli, 1.0)
    expenses_36m = project_value(monthly_needs, coli, 3.0)

    # savings trajectory (naive: assume user continues current savings behavior)
    monthly_current_savings = max(0.0, income - fixed - variable - emi)
    sav_6m = current_savings + monthly_current_savings * 6
    sav_12m = current_savings + monthly_current_savings * 12
    sav_36m = current_savings + monthly_current_savings * 36

    # goal probability heuristic (if user provided goals as dicts)
    goals = payload.get("goals", [])  # expected: list of {"name":..., "target":..., "deadline_months":...}
    goals_out = []
    for g in goals:
        name = g.get("name")
        target = float(g.get("target", 0))
        deadline = int(g.get("deadline_months", 0))
        months_needed = months_to_reach(target - current_savings if target > current_savings else 0, monthly_current_savings)
        # probability heuristic
        if months_needed <= max(1, deadline):
            prob = 85
        elif months_needed <= deadline * 2:
            prob = 55
        else:
            prob = 20
        goals_out.append({
            "goal": name,
            "target": target,
            "deadline_months": deadline,
            "months_needed_at_current_rate": months_needed,
            "probability_percent": prob
        })

    # broke / risk probability heuristic
    # if monthly_current_savings <= 0 and current_savings < emergency_recommended => high risk
    if monthly_current_savings <= 0:
        if current_savings < emergency_recommended:
            broke_prob = 85
        else:
            broke_prob = 60
    else:
        # lower risk if savings cover >=3 months
        cover_months = current_savings / max(1.0, monthly_needs)
        if cover_months >= 6:
            broke_prob = 10
        elif cover_months >= 3:
            broke_prob = 30
        else:
            # compute inverse of savings rate
            broke_prob = min(90, int(max(20, 70 - (savings_rate))))
    # wealth index (0-100)
    wealth_index = max(0, min(100, int((savings_rate * 0.6) + (cover_months if 'cover_months' in locals() else 0) * 4)))
    # clamp
    wealth_index = min(100, wealth_index)

    summary = {
        "income": income,
        "fixed_expenses": fixed,
        "variable_expenses": variable,
        "emi_obligations": emi,
        "current_savings": current_savings,
        "dependents": dependents,
        "monthly_current_savings": monthly_current_savings,
        "savings_rate_percent": savings_rate,
        "emergency_recommended": emergency_recommended,
        "growth_rate": growth_rate,
        "coli_rate": coli,
        "income_projection": {
            "6_months": round(income_6m, 2),
            "12_months": round(income_12m, 2),
            "36_months": round(income_36m, 2)
        },
        "expenses_projection": {
            "6_months": round(expenses_6m, 2),
            "12_months": round(expenses_12m, 2),
            "36_months": round(expenses_36m, 2)
        },
        "savings_projection": {
            "6_months": round(sav_6m, 2),
            "12_months": round(sav_12m, 2),
            "36_months": round(sav_36m, 2)
        },
        "goals": goals_out,
        "broke_probability_percent": broke_prob,
        "wealth_index": wealth_index
    }
    return summary

# ----------------------------
# Build Gemini prompt + one call
# ----------------------------

LIFESTYLE_SYSTEM = (
    "You are a professional financial life coach and planner. You will be given a set of "
    "numerical projections and must produce an advisor-style assessment. Use the facts and do NOT invent numbers. "
       "Indian economy, Indian tax rules, cost of living across Indian cities, and Indian rupee valuations. "
        "IMPORTANT: All numbers MUST be expressed strictly in Indian Rupees (₹). "
    "Return ONLY valid JSON (no explanation) following the schema described."
)

LIFESTYLE_PROMPT_TEMPLATE = """
FACTS:
{facts_json}

TASK:
1) Provide a short Trajectory Summary (1-3 sentences).
2) Provide a Path Verdict: one of ['RIGHT_PATH','MIXED','WRONG_PATH'] with a concise rationale.
3) Provide top 4 Danger Alerts (if any) as strings.
4) Provide 4 prioritized Actionable Changes (each as short sentence).
5) Give Income Growth Advice:
   - If projected 12-month income increase percent is:
     * <=15% => "normal rise" actions,
     * 15-30% => "strong growth" actions,
     * >30% => "drastic increase" actions.
6) For each of the horizons (6 months, 12 months, 36 months) provide a short bullet summary of expected net savings and main risk.
7) For each user goal (if present) provide a short sentence on probability and what to change to improve it.
8) Return the JSON structure exactly as:

{{
  "trajectory_summary": "string",
  "path_verdict": "RIGHT_PATH|MIXED|WRONG_PATH",
  "danger_alerts": ["string",...],
  "actions": ["string",...],
  "income_growth_advice": "string",
  "horizon_highlights": {{
      "6_months": "string",
      "12_months": "string",
      "36_months": "string"
  }},
  "goal_evaluations": [ {{ "goal":"", "probability_percent":0, "note":"" }} ],
  "metrics": {{
      "income_projection": {{}},
      "expenses_projection": {{}},
      "savings_projection": {{}},
      "broke_probability_percent": 0,
      "wealth_index": 0
  }},
  "debug_facts": {{}}
}}
"""


def orchestrate_lifestyle_projection(payload: Dict[str, Any], model_name: str = "gemini-2.5-pro") -> Dict[str, Any]:
    """
    payload: expects keys like monthly_income, fixed_expenses, variable_expenses,
             emi_obligations, current_savings, number_of_dependents, risk_profile, goals (optional)
    """
    if client is None:
        raise RuntimeError("Gemini client not initialized. Set GEMINI_API_KEY")

    # 1) compute deterministic summary
    facts = compute_financial_summary(payload)

    # compute percent increase for 12-month income
    income_current = facts["income"]
    income_12 = facts["income_projection"]["12_months"]
    increase_percent = 0.0
    if income_current > 0:
        increase_percent = round(((income_12 - income_current) / income_current) * 100, 2)

    # Add derived fields to be passed to model
    facts_for_model = dict(facts)
    facts_for_model["projected_income_increase_percent_12m"] = increase_percent

    # 2) Build prompt and call Gemini (single call)
    prompt = LIFESTYLE_PROMPT_TEMPLATE.format(facts_json=json.dumps(facts_for_model, indent=2))

    # system instruction + prompt as raw contents (Gemini SDK accepts plain contents)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=LIFESTYLE_SYSTEM, response_mime_type="application/json")
    )

    # 3) parse response (robust)
    try:
        parsed = json.loads(response.text)
    except Exception:
        txt = response.text
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1:
            parsed = json.loads(txt[start:end+1])
        else:
            raise RuntimeError("Failed to parse JSON from Gemini response")

    # 4) attach deterministic metrics for transparency
    parsed.setdefault("metrics", {})
    parsed["metrics"].update({
        "income_projection": facts["income_projection"],
        "expenses_projection": facts["expenses_projection"],
        "savings_projection": facts["savings_projection"],
        "broke_probability_percent": facts["broke_probability_percent"],
        "wealth_index": facts["wealth_index"]
    })

    parsed.setdefault("debug_facts", {})
    parsed["debug_facts"] = facts_for_model

    return parsed
