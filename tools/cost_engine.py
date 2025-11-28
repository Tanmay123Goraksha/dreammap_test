import json
import os
import re
from typing import Dict, Any, Tuple, Optional

from dotenv import load_dotenv
load_dotenv()

# If you use Gemini, import it; otherwise the code will gracefully skip
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception:
    client = None

TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), "dream_templates.json")
with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
    TEMPLATES = json.load(f)


def _keyword_classify(dream_text: str) -> str:
    """
    Fallback cheap classifier using keywords.
    Returns a template key (category).
    """
    t = dream_text.lower()
    # map keywords to template keys
    mapping = {
        "bike": "purchase_vehicle",
        "motorcycle": "purchase_vehicle",
        "scooter": "purchase_vehicle",
        "phone": "purchase_phone",
        "smartphone": "purchase_phone",
        "laptop": "purchase_laptop",
        "travel": "world_tour",
        "trip": "world_tour",
        "europe": "world_tour",
        "cafe": "start_cafe",
        "coffee": "start_cafe",
        "gym": "open_gym",
        "car": "purchase_car",
        "mba": "masters_degree",
        "masters": "masters_degree",
        "renovate": "home_renovation",
        "wedding": "marriage_planning",
        "marriage": "marriage_planning",
        "dog": "buy_dog",
        "puppy": "buy_dog",
        "horse": "buy_horse",
        "watch": "buy_luxury_item",
        "guitar": "buy_luxury_item",
        "salon": "small_business_service",
        "tutoring": "small_business_service",
        "course": "education_course",
        "furniture": "furniture_purchase",
        "appliance": "home_appliance"
    }
    for kw, key in mapping.items():
        if kw in t:
            return key
    return "other"


def classify_dream(dream_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Try to classify using LLM (one small call), otherwise use keyword fallback.
    Returns (template_key, template_obj).
    """
    # Attempt 1: LLM classification (single call, small)
    prompt = (
        "Classify the following user dream into one of the short categories (single token) "
        "from this list: " + ", ".join(list(TEMPLATES.keys())) + ".\n\n"
        f"User dream: '''{dream_text}'''\n\n"
        "Only respond with the template key (e.g., purchase_vehicle) and nothing else."
    )

    if client:
        try:
            model = "gemini-1.5-flash"  # cheaper, higher quota
            resp = client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                config=types.GenerateContentConfig(response_mime_type="text")
            )
            text = resp.text.strip().lower()
            # Very small sanity filter: only accept known keys
            for key in TEMPLATES.keys():
                if key in text:
                    return key, TEMPLATES[key]
        except Exception:
            # LLM failed or quota; fallback below
            pass

    # Fallback keyword classification
    key = _keyword_classify(dream_text)
    return key, TEMPLATES.get(key, TEMPLATES["other"])


def _parse_numeric_estimate_from_text(text: str) -> Optional[float]:
    """
    Extract first numeric rupee or plain number.
    """
    if not text:
        return None
    txt = text.replace(",", "")
    m = re.search(r"₹\s*([0-9]+(?:\.[0-9]+)?)", txt)
    if m:
        try:
            return float(m.group(1))
        except:
            pass
    m = re.search(r"([0-9]{4,})", txt)
    if m:
        try:
            return float(m.group(1))
        except:
            pass
    return None


def estimate_total_cost_with_ai(dream_text: str, template_key: str) -> Optional[float]:
    """
    Try a small LLM call to return a numeric total estimate (single number).
    If LLM is unavailable or quota exceeds, return None so caller uses base_estimate.
    """
    if not client:
        return None

    prompt = (
        f"Give a single concise numeric estimate (in INR) for the user's dream, no explanation.\n"
        f"Dream: '''{dream_text}'''\n"
        f"Context: category = {template_key}. Provide only a number, optionally with '₹'. Prefer round numbers.\n"
        "If unsure, return nothing."
    )
    try:
        model = "gemini-2.5-pro"
        resp = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="text")
        )
        text = resp.text.strip()
        parsed = _parse_numeric_estimate_from_text(text)
        return parsed
    except Exception:
        return None


def build_breakdown_from_template(template: Dict[str, Any], total_estimate: float) -> Dict[str, Dict[str, Any]]:
    """
    Convert template factors into itemized INR breakdown.
    """
    breakdown = {}
    raw_sum = 0.0
    for item in template["items"]:
        name = item["name"]
        # cost = round(total * factor)
        cost = round(total_estimate * float(item["factor"]))
        breakdown[name] = {
            "item_name": name,
            "estimated_cost_inr": cost,
            "raw_tool_response": f"Computed from template '{template.get('label')}' factor {item['factor']}"
        }
        raw_sum += cost

    # Adjust rounding errors: if difference exists, add to "Misc buffer" or last item
    diff = int(total_estimate - raw_sum)
    if diff != 0:
        # try to find "Misc buffer" item
        misc_found = None
        for k in breakdown:
            if "misc" in k.lower() or "buffer" in k.lower() or "contingency" in k.lower():
                misc_found = k
                break
        if misc_found:
            breakdown[misc_found]["estimated_cost_inr"] += diff
            breakdown[misc_found]["raw_tool_response"] += f" (adjusted +{diff})"
        else:
            # add adjustment to last item
            last_key = list(breakdown.keys())[-1]
            breakdown[last_key]["estimated_cost_inr"] += diff
            breakdown[last_key]["raw_tool_response"] += f" (adjusted +{diff})"

    return breakdown
