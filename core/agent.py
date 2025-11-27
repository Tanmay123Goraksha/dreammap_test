# GoalAura_AI/core/agent.py
import os
import json
import re # Added for robust text processing
from google import genai
from google.genai import types
from dotenv import load_dotenv

from core.models import FinancialGoal, FinancialRoadmap
from tools.financial_tools import get_real_world_cost

# Define the tool for Google GenAI
get_real_world_cost_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_real_world_cost",
            description="Finds the estimated real-world cost for a specific item based on a search query and location, in INR.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "item_query": types.Schema(
                        type=types.Type.STRING,
                        description="The item or service to find the cost for."
                    ),
                    "location": types.Schema(
                        type=types.Type.STRING,
                        description="The location for the cost estimate."
                    )
                },
                required=["item_query"]
            )
        )
    ]
)

# Load environment variables
load_dotenv()
# Note: Client initialization might fail if key is not found, handled by the check below
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    print(f"Warning: Gemini client initialization failed. Check API key: {e}")

def orchestrate_dream_mapping(dream_text: str, user_income: float) -> FinancialRoadmap:
    """
    The main Agentic loop that interprets the dream, finds costs, and generates the roadmap.
    """
    model_name = "gemini-2.5-pro"
    
    # Check 1: API Key existence (redundant check from main.py, but safe)
    if not os.environ.get("GEMINI_API_KEY"):
         raise ValueError("GEMINI_API_KEY is not set. Cannot run AI agent.")
    
    # --- STEP 1: Goal Interpretation (Structured Output) ---
    print("\n--- Agent Step 1: Interpreting Dream ---")
    
    prompt_interpretation = f"Analyze this user dream and structure it according to the FinancialGoal schema. Dream: '{dream_text}'"
    
    interpretation_response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_interpretation)])
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FinancialGoal,
        ),
    )
    structured_goal = FinancialGoal(**json.loads(interpretation_response.text))
    print(f"Agent Action: Interpreted Goal: {structured_goal.goal_name}")
    
    # --- STEP 2: Reverse Budget Engineering (Tool Calling) ---
    print("\n--- Agent Step 2: Reverse Engineering Budget ---")
    
    budget_system_instruction = (
        "You are a Reverse Budget Engineer. Your task is to use the `get_real_world_cost` tool "
        "to find the cost of the main item needed for the goal, then calculate a **Total Estimated Budget** "
        "by adding 25% to the primary cost for miscellaneous expenses (licenses, initial stock, marketing, etc.)."
    )
    
    # 2a. First call: Gemini decides to call the tool
    prompt_for_cost = f"Find the real-world cost for the primary item: {structured_goal.estimated_primary_cost_item}. The location is Mumbai, India."
    
    cost_response_1 = client.models.generate_content(
        model=model_name,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt_for_cost)])],
        config=types.GenerateContentConfig(system_instruction=budget_system_instruction, tools=[get_real_world_cost_tool]),
    )
    
    # 2b. Execute the tool and send result back to Gemini
    if not cost_response_1.function_calls:
        # If the model fails to call the tool, it usually hallucinates a text response instead
        raise Exception(f"Agent failed to call the cost tool. Model Response: {cost_response_1.text[:100]}...")

    function_call = cost_response_1.function_calls[0]
    tool_output = get_real_world_cost(**dict(function_call.args))
    
    print(f"Agent Action: Executed Tool: get_real_world_cost. Output: {tool_output[:50]}...")
    
    # The fix is ensuring the contents list is correctly structured below:
    cost_response_2 = client.models.generate_content(
        model=model_name,
        contents=[
            # This is the original user message
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_for_cost)]),

            # This is the tool's output being sent back to the model
            types.Content(
                role="function",
                parts=[
                    types.Part.from_function_response(
                        name=function_call.name,
                        response={"result": tool_output}
                    )
                ]
            )
        ],
        config=types.GenerateContentConfig(system_instruction=budget_system_instruction, tools=[get_real_world_cost]),
    )
    
    budget_analysis_text = cost_response_2.text
    
    # --- STEP 3: Timeline & Roadmap Generation (Structured Output) ---
    print("\n--- Agent Step 3: Generating Roadmap ---")

    roadmap_system_instruction = (
        f"You are a Financial Planner. Use the budget analysis to extract the **Total Estimated Budget**. "
        f"Generate a final {structured_goal.user_timeline_preference} roadmap according to the FinancialRoadmap schema. "
        f"Use the following fixed timelines for the options: Aggressive (6 months), Comfortable (12 months), Luxury (24 months). "
        f"User's monthly income is ₹{user_income}. Calculate the required monthly savings and percentage of income for each path."
    )
    
    prompt_for_roadmap = f"Generate the full financial roadmap using this budget analysis: {budget_analysis_text}"
    
    roadmap_response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_for_roadmap)])
        ],
        config=types.GenerateContentConfig(
            system_instruction=roadmap_system_instruction,
            response_mime_type="application/json",
            response_schema=FinancialRoadmap,
        ),
    )

    final_roadmap = FinancialRoadmap(**json.loads(roadmap_response.text))
    print(f"Agent Action: Generated Roadmap with {len(final_roadmap.timeline_options)} options.")
    
    return final_roadmap

# --- Example of running the whole agent pipeline ---
if __name__ == "__main__":
    dream = "I want to start a small, high-end home bakery within the next 6 months. I need the best equipment, no compromises on quality. I can manage to save a good amount monthly if it means hitting the aggressive timeline."
    income = 50000.00 # Example income in INR

    if not os.environ.get("GEMINI_API_KEY"):
        print("Please set your GEMINI_API_KEY in the .env file or environment.")
    else:
        try:
            result_roadmap = orchestrate_dream_mapping(dream, income)
            print("\n" + "="*50)
            print("✨ FINAL GOALAURA FINANCIAL ROADMAP ✨")
            print("="*50)
            print(result_roadmap.model_dump_json(indent=2))
        except Exception as e:
            # Added better error context
            print(f"\nFATAL ERROR DURING ORCHESTRATION: {type(e).__name__}: {e}")
            print("Please ensure your API Key is valid and the model definitions in models.py match the schema.")