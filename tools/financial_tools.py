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


def get_real_world_cost(item_query: str, location: str = "Mumbai, India") -> str:
    """
    UNIVERSAL mock cost tool.

    - Handles ANY item the user wants
    - Known items return realistic structured costs
    - Unknown items fall back to a generic estimate
    """

    q = item_query.lower()

    # --- Known objects (still allowed but optional) ---
    KNOWN_ITEMS = {
        "commercial oven": "₹100000",
        "gaming pc": "₹120000",
        "horse": "₹300000",
        "dog": "₹40000",
        "bicycle": "₹15000",
        "motorcycle": "₹150000",
        "car": "₹800000",
    }

    for key, price in KNOWN_ITEMS.items():
        if key in q:
            return f"Estimated cost for {key} in {location} is approximately {price}."

    # --- Universal fallback (works for anything the user types) ---
    return (
        f"No exact market data found for '{item_query}'. "
        f"Using a generic project/startup estimate of ₹100,000."
    )


def parse_price_inr(text: str) -> float:
    return _extract_first_numeric_rupee(text)
