# GoalAura_AI/tools/financial_tools.py

def get_real_world_cost(item_query: str, location: str = "Mumbai, India") -> str:
    """
    Finds the estimated real-world cost for a specific item (e.g., equipment, service)
    based on a search query and location. Used for reverse budget engineering.
    """
    # *** HACKATHON SIMULATION LOGIC ***
    # The AI will interpret the text and extract the number to use in its calculation.
    if "commercial oven" in item_query.lower() or "best equipment" in item_query.lower():
        # Total cost for primary equipment: 130,000 INR
        return "The total cost for the commercial oven and high-end stand mixer is estimated to be ₹130,000."
    elif "retire parents" in item_query.lower():
        # Retirement corpus estimate: 1.2 Crores INR
        return "An estimate for a retirement corpus yielding ₹50,000 per month for 20 years in India is approximately ₹1,20,00,000."
    else:
        return f"Cannot find specific cost for '{item_query}'. Assuming a general project startup cost of ₹100,000."