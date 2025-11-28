# core/quantum_tree.py
import os
import time
import json
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Use existing _safe_generate_content from your code or import if it's in a shared module.
# If it's in core.agent you can import; otherwise paste _safe_generate_content here.
# For safety, we replicate a tiny wrapper that uses the global `client` if available.

load_dotenv()

# Initialize Gemini client similarly to your other files (safe guard)
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    client = None
    print(f"Warning: Gemini client init failed in quantum_tree: {e}")

def _safe_generate_content(*, model: str, contents, config):
    if client is None:
        raise RuntimeError("GenAI client not initialized. Set GEMINI_API_KEY in env.")
    return client.models.generate_content(model=model, contents=contents, config=config)

# Simple in-process rate limiter (per-process). Keeps up to 2 calls per 60s.
_rate_limit_state = {"timestamps": []}
_RATE_LIMIT_MAX = 2
_RATE_LIMIT_WINDOW = 60  # seconds

def _check_rate_limit():
    now = time.time()
    ts = _rate_limit_state["timestamps"]
    # filter to last window
    ts[:] = [t for t in ts if now - t < _RATE_LIMIT_WINDOW]
    if len(ts) >= _RATE_LIMIT_MAX:
        # Too many requests in window
        return False, _RATE_LIMIT_WINDOW - (now - ts[0])
    ts.append(now)
    return True, 0.0

# -------------------------
# Local numeric helper funcs
# -------------------------
def future_value(amount: float, annual_rate: float, years: float) -> float:
    return amount * ((1 + annual_rate) ** years)

def months_to_save(amount: float, monthly_saved: float) -> int:
    if monthly_saved <= 0:
        return 9999
    return int((amount + monthly_saved - 1) // monthly_saved)

def percent_of(value: float, base: float) -> float:
    if base <= 0:
        return 0.0
    return round((value / base) * 100, 2)

def simulate_goal_impact(existing_goals: List[Dict[str, Any]], delay_months: int, purchase_cost: float, monthly_savings: float) -> List[Dict[str, Any]]:
    """
    Very simple simulation: reduce monthly savings for `delay_months` and see new completion months.
    existing_goals: [{"name":..,"target_amount":..,"deadline_months":..}]
    """
    out = []
    for g in existing_goals:
        target = float(g.get("target_amount", 0))
        deadline = int(g.get("deadline_months", 12))
        # naive current monthly contribution
        if monthly_savings <= 0:
            months_now = 9999
        else:
            months_now = max(1, int((target + monthly_savings - 1) // monthly_savings))
        # after spending purchase_cost, assume user's monthly savings reduces proportionally for one period:
        if monthly_savings <= 0:
            months_after = 9999
        else:
            # assume the user diverts the monthly saving equivalent to amortize purchase over delay_months
            diverted = purchase_cost / max(1, delay_months)
            effective_monthly = max(0.0, monthly_savings - diverted)
            months_after = int((target + effective_monthly - 1) // effective_monthly) if effective_monthly > 0 else 9999
        out.append({
            "name": g.get("name", "Unnamed Goal"),
            "target_amount": target,
            "deadline_months": deadline,
            "months_to_complete_now": months_now,
            "months_to_complete_if_purchase_now": months_after,
            "delay_months_estimated": max(0, months_after - months_now) if months_now < 9999 else None
        })
    return out

# -------------------------
# Orchestrator function
# -------------------------
def orchestrate_quantum_decision_tree(
    purchase_item: str,
    purchase_cost: float,
    user_monthly_income: float,
    user_monthly_fixed_expenses: float,
    user_monthly_savings: float,
    existing_goals: Optional[List[Dict[str, Any]]] = None,
    impulse_score: Optional[int] = 5,            # 1-10
    emotional_state: Optional[str] = "neutral",
    time_sensitivity: Optional[str] = "normal",  # "urgent","normal","flexible"
    depreciation_rate_ann=0.25,                  # default for electronics (25%/yr)
    investment_return_rate=0.10,                 # default 10% p.a.
    delay_days_options: Optional[List[int]] = None,
    model_name: str = "gemini-2.5-pro"
) -> Dict[str, Any]:
    """
    Build professional Q-FDT output with minimal Gemini calls:
    1) perform numeric simulations locally (affordability, future values, goal impact)
    2) call Gemini once to produce human-friendly executive summary, probability estimates, and final recommendation
    """

    # Rate limiter check
    ok, retry_after = _check_rate_limit()
    if not ok:
        return {
            "error": "Rate limit exceeded. Try again in {:.0f} seconds.".format(retry_after)
        }

    existing_goals = existing_goals or []
    delay_days_options = delay_days_options or [14, 30, 90]  # default postponement horizons

    # Local calculations: affordability
    disposable_income = max(0.0, user_monthly_income - user_monthly_fixed_expenses)
    purchase_pct_of_disposable = percent_of(purchase_cost, disposable_income) if disposable_income > 0 else None
    months_savings_impact = months_to_save(purchase_cost, user_monthly_savings)

    # Future value if invested instead of spent
    fv_1yr = future_value(purchase_cost, investment_return_rate, 1)
    fv_5yr = future_value(purchase_cost, investment_return_rate, 5)
    fv_10yr = future_value(purchase_cost, investment_return_rate, 10)

    # Depreciation projections (naive) for buy-now scenario
    def depreciated_value(initial, year, rate):
        return initial * ((1 - rate) ** year) if rate < 1 else 0.0

    dep_1yr = depreciated_value(purchase_cost, 1, depreciation_rate_ann)
    dep_5yr = depreciated_value(purchase_cost, 5, depreciation_rate_ann)
    dep_10yr = depreciated_value(purchase_cost, 10, depreciation_rate_ann)

    # Goal impact simulation using helper
    goals_impact = simulate_goal_impact(existing_goals, max(1, int(delay_days_options[0] / 30)), purchase_cost, user_monthly_savings)

    # Build the context / facts block to feed Gemini
    facts = {
        "purchase_item": purchase_item,
        "purchase_cost": purchase_cost,
        "disposable_income": disposable_income,
        "purchase_pct_of_disposable": purchase_pct_of_disposable,
        "months_savings_impact": months_savings_impact,
        "fv": {"1y": fv_1yr, "5y": fv_5yr, "10y": fv_10yr},
        "depreciation": {"1y": dep_1yr, "5y": dep_5yr, "10y": dep_10yr},
        "goals_impact_summary": goals_impact,
        "behavior": {"impulse_score": impulse_score, "emotional_state": emotional_state, "time_sensitivity": time_sensitivity},
        "assumptions": {"investment_return_rate": investment_return_rate, "depreciation_rate_ann": depreciation_rate_ann}
    }

    # Build a concise system instruction and user prompt that asks Gemini for structured JSON
    system_instruction = (
        "You are GoalAura's certified-like financial advisor assistant. Use the facts provided to "
        "produce a professional, concise, and actionable advisory report. Return valid JSON only."
    )

    # We instruct model to produce a JSON object with the fields defined below. We rely on numeric sims above.
    user_prompt = (
        "FACTS:\n" + json.dumps(facts, indent=2) +
        "\n\nTASK:\n"
        "Using the facts above, generate a JSON object with these keys:\n"
        "1) executive_summary: short string (one sentence) recommendation: 'Approved'|'Approved with Conditions'|'Not Recommended'\n"
        "2) affordability_analysis: { disposable_income, purchase_pct_of_disposable, months_savings_impact }\n"
        "3) goal_impact: copy/expand the goals_impact_summary and for each goal provide a short impact_note\n"
        "4) behavioral_risk: { regret_probability (0-1), rationale }\n"
        "5) scenarios: an array with exactly three named scenarios ('Buy Now','Delay 30 days','Do Not Buy'). For each scenario provide:\n"
        "   - name, net_cost_over_1yr, net_cost_over_5yr, expected_emotional_outcome, probability (0-1), recommendation (short)\n"
        "6) final_recommendation: which scenario and 2 actionable next steps (short list)\n"
        "\nImportant constraints:\n"
        "- Use the numerical results from the FACTS block for calculations and reasoning. Do NOT invent new numeric values unless noted. If you cannot compute a probability, estimate reasonably and mark as 'estimated'.\n"
        "- Keep all numeric fields as numbers (no commas). Return valid JSON ONLY.\n"
        "\nReturn the JSON only, no extra text."
    )

    # Make a single Gemini call (one LLM call) to synthesize language, probabilities & summary
    try:
        response = _safe_generate_content(
            model=model_name,
            contents=[types.Content(role="user", parts=[types.Part.from_text(user_prompt)])],
            config=types.GenerateContentConfig(system_instruction=system_instruction, response_mime_type="application/json")
        )
        # response.text is expected to be JSON
        result_json = None
        try:
            result_json = json.loads(response.text)
        except Exception:
            # fallback: attempt to extract JSON substring
            text = response.text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    result_json = json.loads(text[start:end+1])
                except Exception:
                    result_json = {"error": "Failed to parse model JSON output", "raw": text}
            else:
                result_json = {"error": "No JSON found in model output", "raw": response.text}

    except Exception as e:
        print(f"Quantum tree model call failed: {e}")
        result_json = {"error": "Model call failed", "exception": str(e)}

    # Augment result with deterministic numeric fields for transparency
    result_json = result_json or {}
    result_json.setdefault("debug_facts", {})  # ensure present
    result_json["debug_facts"].update({
        "computed": facts,
        "note": "Most numeric values computed locally; model produced qualitative synthesis."
    })

    return result_json
