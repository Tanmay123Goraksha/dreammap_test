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

def generate_dynamic_roadmap(
    dream_text: str, 
    estimated_budget: float,
    user_income: float, 
    target_months: int
) -> DreamRoadmap:
    """
    Enhanced AI processing: Brutally honest, realistic roadmap with detailed action plans.
    Handles unrealistic dreams and provides proper guidance.
    
    Args:
        dream_text: User's goal description
        estimated_budget: User's budget estimate in INR
        user_income: Monthly income in INR
        target_months: Timeline to achieve the dream
    
    Returns:
        DreamRoadmap with honest assessment and actionable steps
    """
    model_name = "gemini-2.0-flash-exp"

    if not os.environ.get("GEMINI_API_KEY"):
        return DreamRoadmap(
            dreamType="unknown",
            isRealistic=False,
            realityCheck="AI unavailable - cannot assess feasibility",
            estimatedCost=estimated_budget,
            userBudget=estimated_budget,
            budgetGap=0,
            months=target_months,
            monthlySaving=estimated_budget / target_months,
            savingPercentage=0.0,
            feasibilityScore=5,
            actionPlan=["AI unavailable — fallback activated"],
            challenges=["Cannot assess without AI"],
            proTips=["Configure API key to get detailed guidance"]
        )

    # --- STEP 1: Get real-world cost estimate ---
    dream_type, _ = classify_dream(dream_text)
    cost_response = get_real_world_cost(dream_text, "Mumbai, India")
    estimated_cost = parse_price_inr(cost_response)
    if estimated_cost <= 0:
        estimated_cost = estimated_budget * 1.2  # Assume 20% higher than budget

    # Calculate financial metrics
    budget_gap = estimated_cost - estimated_budget
    monthly_saving = round(estimated_cost / target_months, 2)
    saving_percentage = round((monthly_saving / user_income) * 100, 2) if user_income > 0 else 0.0
    
    # Determine if realistic
    is_realistic = (
        estimated_budget >= estimated_cost * 0.8 and  # Budget is at least 80% of cost
        saving_percentage <= 50 and  # Not requiring more than 50% of income
        target_months >= 1
    )
    
    # Calculate feasibility score (1-10)
    feasibility_score = 10
    if budget_gap > estimated_cost * 0.5:
        feasibility_score -= 4
    elif budget_gap > estimated_cost * 0.2:
        feasibility_score -= 2
    
    if saving_percentage > 50:
        feasibility_score -= 3
    elif saving_percentage > 30:
        feasibility_score -= 1
    
    if target_months < 3:
        feasibility_score -= 2
    
    feasibility_score = max(1, min(10, feasibility_score))

    # --- STEP 2: Generate brutally honest, detailed roadmap with AI ---
    prompt = f"""
You are a brutally honest financial advisor. Analyze this dream and provide REALISTIC, ACTIONABLE guidance.

**User's Dream:** {dream_text}
**Dream Category:** {dream_type}
**User's Budget Estimate:** ₹{estimated_budget:,.0f}
**Real Market Cost:** ₹{estimated_cost:,.0f}
**Budget Gap:** ₹{budget_gap:,.0f} ({"OVER budget" if budget_gap > 0 else "UNDER budget"})
**User's Monthly Income:** ₹{user_income:,.0f}
**Target Timeline:** {target_months} months
**Required Monthly Saving:** ₹{monthly_saving:,.0f} ({saving_percentage:.1f}% of income)
**Is Realistic:** {"Yes" if is_realistic else "No"}

**Your Task:**
Be BRUTALLY HONEST. If the dream is unrealistic, say so clearly. Provide SPECIFIC, ACTIONABLE steps with real-world details.

Return a JSON object with:

1. **realityCheck** (string): 
   - Be honest about feasibility
   - If unrealistic, explain why clearly
   - If realistic, acknowledge it but mention challenges
   - Use specific numbers from the data
   - 2-4 sentences

2. **actionPlan** (array of 7-10 strings):
   - DETAILED, step-by-step action plan
   - Each step should be SPECIFIC and ACTIONABLE
   - Include timelines, amounts, and concrete actions
   - Start with research/planning, move to execution
   - Examples:
     * "Month 1-2: Research [specific thing]. Visit [specific places]. Compare [specific options]. Budget: ₹X"
     * "Month 3: Open dedicated savings account. Set up auto-transfer of ₹X on salary day"
     * "Month 4-6: Save ₹X/month by cutting [specific expenses]. Track progress weekly"
   - Make it feel like a real plan someone can follow

3. **challenges** (array of 4-6 strings):
   - REAL obstacles they will face
   - Be specific to their situation
   - Include financial, practical, and emotional challenges
   - Examples:
     * "Maintaining ₹X/month savings when unexpected expenses arise"
     * "Resisting impulse purchases in [category] which currently costs ₹Y/month"
     * "Market price fluctuations - [item] prices can vary by 10-15%"

4. **alternatives** (array of 3-5 strings, or null if dream is realistic):
   - Only if dream is UNREALISTIC
   - Provide practical alternatives
   - Be specific with numbers
   - Examples:
     * "Extend timeline to X months to reduce monthly burden to ₹Y"
     * "Consider [alternative option] which costs ₹X less"
     * "Start with [smaller version] for ₹X, upgrade later"

5. **proTips** (array of 4-6 strings):
   - INSIDER KNOWLEDGE and practical tips
   - Specific to this dream category
   - Include money-saving strategies
   - Examples:
     * "Buy during [specific season/month] for 15-20% discounts"
     * "Negotiate [specific aspect] to save ₹X-Y"
     * "Use [specific platform/method] to get better deals"
     * "Avoid [specific mistake] that costs ₹X extra"

**CRITICAL RULES:**
- Be HONEST, not encouraging if it's unrealistic
- Every step must be ACTIONABLE with specific details
- Include actual numbers, timelines, and concrete actions
- No generic advice like "save money" - be specific
- If budget is way off, say so clearly
- Consider Indian market context (Mumbai/India)
"""

    try:
        # **CRITICAL FIX:** Use positional argument for types.Part.from_text
        response = _safe_generate_content(
            model=model_name,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.8
            ),
        )
        
        ai_response = json.loads(response.text)
        
        return DreamRoadmap(
            dreamType=dream_type,
            isRealistic=is_realistic,
            realityCheck=ai_response.get("realityCheck", "Assessment completed"),
            estimatedCost=estimated_cost,
            userBudget=estimated_budget,
            budgetGap=budget_gap,
            months=target_months,
            monthlySaving=monthly_saving,
            savingPercentage=saving_percentage,
            feasibilityScore=feasibility_score,
            actionPlan=ai_response.get("actionPlan", ["Plan generation failed"]),
            challenges=ai_response.get("challenges", ["Assessment needed"]),
            alternatives=ai_response.get("alternatives") if not is_realistic else None,
            proTips=ai_response.get("proTips", ["Tips unavailable"])
        )
        
    except Exception as e:
        print(f"Roadmap generation failed: {e}")
        
        # Generate fallback with calculated insights
        reality_check = ""
        if budget_gap > estimated_cost * 0.3:
            reality_check = f"REALITY CHECK: Your budget of ₹{estimated_budget:,.0f} is ₹{budget_gap:,.0f} short. Real cost is ₹{estimated_cost:,.0f}. This needs serious reconsideration."
        elif saving_percentage > 40:
            reality_check = f"CHALLENGING: Saving ₹{monthly_saving:,.0f}/month ({saving_percentage:.1f}% of income) is very aggressive. Most experts recommend max 30-40%."
        else:
            reality_check = f"ACHIEVABLE: Budget is close to real cost. Saving {saving_percentage:.1f}% of income is manageable with discipline."
        
        action_plan = [
            f"Month 1: Research {dream_type} options. Set target: ₹{estimated_cost:,.0f}. Create dedicated savings account.",
            f"Month 1-2: Analyze current spending. Identify ₹{monthly_saving:,.0f}/month to cut. Set up auto-transfer.",
            f"Month 2-{target_months//2}: Save consistently. Track weekly. Adjust if needed. Target: ₹{estimated_cost/2:,.0f}.",
            f"Month {target_months//2}: Review progress. Research current market prices. Adjust plan if prices changed.",
            f"Month {target_months//2+1}-{target_months-1}: Continue saving. Start comparing specific options and deals.",
            f"Month {target_months-1}: Finalize choice. Negotiate price. Ensure all costs included (taxes, fees, etc.).",
            f"Month {target_months}: Complete purchase. Keep emergency buffer of ₹{monthly_saving*2:,.0f} for unexpected costs."
        ]
        
        challenges = [
            f"Maintaining ₹{monthly_saving:,.0f}/month savings discipline for {target_months} months",
            f"Budget gap of ₹{abs(budget_gap):,.0f} between estimate and reality" if budget_gap > 0 else "Staying within budget despite market fluctuations",
            "Unexpected expenses disrupting savings plan",
            "Temptation to compromise on quality to meet budget",
            f"Price increases during {target_months}-month timeline"
        ]
        
        alternatives = None
        if not is_realistic:
            alternatives = [
                f"Extend timeline to {int(target_months * 1.5)} months to reduce monthly saving to ₹{estimated_cost/(target_months*1.5):,.0f}",
                f"Increase budget to ₹{estimated_cost:,.0f} (real market cost)",
                f"Consider used/refurbished options to save 20-30%",
                "Start with basic version, upgrade later"
            ]
        
        pro_tips = [
            f"Research {dream_type} prices across 5+ sources before committing",
            "Negotiate - most sellers have 5-10% flexibility",
            "Buy during sale seasons (festival periods, year-end) for discounts",
            "Check total cost including taxes, registration, insurance, etc.",
            "Keep 10-15% buffer for unexpected costs"
        ]
        
        return DreamRoadmap(
            dreamType=dream_type,
            isRealistic=is_realistic,
            realityCheck=reality_check,
            estimatedCost=estimated_cost,
            userBudget=estimated_budget,
            budgetGap=budget_gap,
            months=target_months,
            monthlySaving=monthly_saving,
            savingPercentage=saving_percentage,
            feasibilityScore=feasibility_score,
            actionPlan=action_plan,
            challenges=challenges[:6],
            alternatives=alternatives,
            proTips=pro_tips
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
