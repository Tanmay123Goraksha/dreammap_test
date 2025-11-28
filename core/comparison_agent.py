import os
import json
import csv
from io import StringIO
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from google import genai
from google.genai import types

from core.models import UserComparisonInsights

load_dotenv()

# Initialize client
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    client = None
    print(f"Warning: Gemini client init failed: {e}")


def _safe_generate_content(*, model: str, contents, config):
    """Wrap model call to provide clearer errors when client is not initialized."""
    if client is None:
        raise RuntimeError("GenAI client not initialized. Set GEMINI_API_KEY in env.")
    return client.models.generate_content(model=model, contents=contents, config=config)


def parse_user_info(user_info: str) -> Dict[str, str]:
    """Parse user info string in format 'job_salary_savings'."""
    parts = user_info.split('_')
    if len(parts) != 3:
        raise ValueError("User info must be in format: job_salary_savings")
    
    return {
        "job": parts[0],
        "salary": parts[1],
        "savings": parts[2]
    }


def parse_csv_transactions(csv_string: str) -> List[Dict]:
    """Parse CSV transaction data from string format."""
    try:
        csv_file = StringIO(csv_string)
        reader = csv.DictReader(csv_file)
        transactions = list(reader)
        return transactions
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return []


def analyze_transactions(transactions: List[Dict]) -> Dict:
    """Analyze transaction patterns to extract spending categories and amounts."""
    categories = {}
    total_spent = 0.0
    
    for txn in transactions:
        # Assuming CSV has 'category' and 'amount' fields
        category = txn.get('category', 'Other')
        try:
            amount = float(txn.get('amount', 0))
            total_spent += amount
            categories[category] = categories.get(category, 0) + amount
        except ValueError:
            continue
    
    return {
        "total_spent": total_spent,
        "categories": categories,
        "transaction_count": len(transactions)
    }


def generate_comparison_insights(
    current_user_info: str,
    other_user_info: str,
    current_user_transactions: str,
    other_user_transactions: str
) -> UserComparisonInsights:
    """
    Compare two users' financial profiles and generate personalized insights.
    
    Args:
        current_user_info: Format "job_salary_savings"
        other_user_info: Format "job_salary_savings"
        current_user_transactions: CSV format transaction data as string
        other_user_transactions: CSV format transaction data as string
    
    Returns:
        UserComparisonInsights with detailed analysis and recommendations
    """
    model_name = "gemini-2.0-flash-exp"
    
    if not os.environ.get("GEMINI_API_KEY"):
        return UserComparisonInsights(
            summary="AI unavailable - fallback mode",
            job_comparison="Unable to compare",
            savings_insights="Unable to analyze",
            spending_patterns=["Data unavailable"],
            recommendations=["Please configure API key"],
            unnecessary_expenses=["Analysis unavailable"],
            peer_benchmark="Benchmark unavailable"
        )
    
    # Parse user information
    try:
        current_user = parse_user_info(current_user_info)
        other_user = parse_user_info(other_user_info)
    except ValueError as e:
        raise ValueError(f"Invalid user info format: {e}")
    
    # Parse and analyze transactions
    current_txns = parse_csv_transactions(current_user_transactions)
    other_txns = parse_csv_transactions(other_user_transactions)
    
    current_analysis = analyze_transactions(current_txns)
    other_analysis = analyze_transactions(other_txns)
    
    # Calculate detailed metrics for data-driven insights
    current_savings_rate = (float(current_user['savings']) / float(current_user['salary'])) * 100 if float(current_user['salary']) > 0 else 0
    other_savings_rate = (float(other_user['savings']) / float(other_user['salary'])) * 100 if float(other_user['salary']) > 0 else 0
    
    spending_diff = current_analysis['total_spent'] - other_analysis['total_spent']
    spending_diff_pct = (spending_diff / other_analysis['total_spent'] * 100) if other_analysis['total_spent'] > 0 else 0
    
    # Build comprehensive prompt for AI analysis
    prompt = f"""
You are a data-driven financial advisor analyzing two users with similar income levels. Provide SPECIFIC, QUANTIFIED recommendations based on actual spending data.

**Current User Profile:**
- Job: {current_user['job']}
- Monthly Salary: ₹{current_user['salary']}
- Current Savings: ₹{current_user['savings']}
- Savings Rate: {current_savings_rate:.1f}%
- Total Spent (analyzed period): ₹{current_analysis['total_spent']}
- Spending by Category: {json.dumps(current_analysis['categories'], indent=2)}
- Number of Transactions: {current_analysis['transaction_count']}

**Comparison User Profile:**
- Job: {other_user['job']}
- Monthly Salary: ₹{other_user['salary']}
- Current Savings: ₹{other_user['savings']}
- Savings Rate: {other_savings_rate:.1f}%
- Total Spent (analyzed period): ₹{other_analysis['total_spent']}
- Spending by Category: {json.dumps(other_analysis['categories'], indent=2)}
- Number of Transactions: {other_analysis['transaction_count']}

**Key Metrics:**
- Current user spends {spending_diff_pct:+.1f}% more/less than comparison user
- Savings rate difference: {current_savings_rate - other_savings_rate:+.1f} percentage points

**Task:**
Provide DATA-DRIVEN financial insights. Every recommendation MUST include specific numbers, percentages, or amounts. Return a JSON object with:

1. "summary": Brief overview with SPECIFIC numbers (e.g., "You spend ₹X more on Y, which is Z% higher")

2. "job_comparison": Compare job profiles with salary context and typical spending patterns for these roles

3. "savings_insights": MUST include:
   - Exact savings rate comparison (X% vs Y%)
   - Monthly savings amount difference in ₹
   - Projected annual savings difference
   - Specific percentage points to improve

4. "spending_patterns": Array of 3-5 patterns with EXACT amounts and percentages:
   - "You spend ₹X on [category] vs peer's ₹Y (Z% difference)"
   - Compare each major category with specific numbers
   - Identify highest variance categories

5. "recommendations": Array of 5-7 DATA-DRIVEN, ACTIONABLE recommendations:
   - "Reduce [category] spending by ₹X (from ₹Y to ₹Z) to match peer levels"
   - "Cut [specific expense] by X% to save ₹Y per month"
   - "Reallocate ₹X from [category A] to [category B/savings]"
   - Each recommendation MUST have specific amounts and expected savings
   - Calculate potential monthly/annual savings for each action

6. "unnecessary_expenses": Array of 3-5 specific expenses with amounts:
   - "[Category]: Currently ₹X, peer spends ₹Y. Reduce by ₹Z to save W% monthly"
   - Focus on categories where current user significantly overspends
   - Include exact reduction targets

7. "peer_benchmark": Compelling insight with job, numbers, and strategy:
   - Format: "[Job]s in [location/context] with ₹X income save Y% more by [specific strategy]"
   - Use actual data from comparison
   - Include actionable strategy that explains the difference

CRITICAL: Every insight must include specific rupee amounts, percentages, or quantified metrics. No generic advice.
"""
    
    try:
        response = _safe_generate_content(
            model=model_name,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            ),
        )
        
        insights_data = json.loads(response.text)
        
        # Validate and create response
        return UserComparisonInsights(
            summary=insights_data.get("summary", "Analysis completed"),
            job_comparison=insights_data.get("job_comparison", "Job profiles analyzed"),
            savings_insights=insights_data.get("savings_insights", "Savings patterns compared"),
            spending_patterns=insights_data.get("spending_patterns", ["Pattern analysis completed"]),
            recommendations=insights_data.get("recommendations", ["Continue monitoring expenses"]),
            unnecessary_expenses=insights_data.get("unnecessary_expenses", ["Review all expenses"]),
            peer_benchmark=insights_data.get("peer_benchmark", "Benchmark analysis completed")
        )
        
    except Exception as e:
        print(f"Error generating comparison insights: {e}")
        
        # Calculate metrics for fallback
        current_savings_rate = (float(current_user['savings']) / float(current_user['salary'])) * 100
        other_savings_rate = (float(other_user['savings']) / float(other_user['salary'])) * 100
        spending_diff = current_analysis['total_spent'] - other_analysis['total_spent']
        savings_gap = float(other_user['savings']) - float(current_user['savings'])
        
        # Generate data-driven fallback insights
        spending_patterns = []
        recommendations = []
        unnecessary_expenses = []
        
        # Compare spending by category
        for category, amount in current_analysis['categories'].items():
            other_amount = other_analysis['categories'].get(category, 0)
            if amount > other_amount:
                diff = amount - other_amount
                diff_pct = (diff / other_amount * 100) if other_amount > 0 else 0
                spending_patterns.append(
                    f"{category}: You spend ₹{amount:.0f} vs peer's ₹{other_amount:.0f} ({diff_pct:+.1f}% more)"
                )
                if diff > 500:  # Significant difference
                    unnecessary_expenses.append(
                        f"{category}: Reduce by ₹{diff:.0f} to match peer levels (save {diff_pct:.0f}% monthly)"
                    )
                    recommendations.append(
                        f"Cut {category} spending from ₹{amount:.0f} to ₹{other_amount:.0f} to save ₹{diff:.0f}/month"
                    )
        
        # Add general recommendations based on data
        if spending_diff > 0:
            recommendations.insert(0, f"Reduce total spending by ₹{spending_diff:.0f} to match peer's efficient spending pattern")
        
        if savings_gap > 0:
            months_to_catch_up = savings_gap / spending_diff if spending_diff > 0 else 12
            recommendations.append(
                f"Save an additional ₹{spending_diff:.0f}/month to close the ₹{savings_gap:.0f} savings gap in {months_to_catch_up:.0f} months"
            )
        
        recommendations.append(
            f"Increase savings rate from {current_savings_rate:.1f}% to {other_savings_rate:.1f}% (target: +{other_savings_rate - current_savings_rate:.1f} percentage points)"
        )
        
        # Ensure we have at least some items
        if not spending_patterns:
            spending_patterns = [f"Total spending: ₹{current_analysis['total_spent']:.0f} vs peer's ₹{other_analysis['total_spent']:.0f}"]
        
        if not unnecessary_expenses:
            unnecessary_expenses = [f"Review all discretionary spending to reduce by ₹{spending_diff:.0f}"]
        
        return UserComparisonInsights(
            summary=f"You spend ₹{spending_diff:.0f} more than your peer ({spending_diff/other_analysis['total_spent']*100:+.1f}%). Savings rate: {current_savings_rate:.1f}% vs peer's {other_savings_rate:.1f}%.",
            job_comparison=f"Both {current_user['job']} roles with ₹{current_user['salary']} and ₹{other_user['salary']} monthly income show different spending behaviors.",
            savings_insights=f"Current savings: ₹{current_user['savings']} ({current_savings_rate:.1f}% rate) vs peer: ₹{other_user['savings']} ({other_savings_rate:.1f}% rate). Gap: ₹{savings_gap:.0f}. By matching peer's spending, you could save ₹{spending_diff:.0f} more per month.",
            spending_patterns=spending_patterns[:5],
            recommendations=recommendations[:7],
            unnecessary_expenses=unnecessary_expenses[:5],
            peer_benchmark=f"{other_user['job']}s with ₹{other_user['salary']} income achieve {other_savings_rate:.1f}% savings rate by spending ₹{other_analysis['total_spent']:.0f} less on discretionary expenses."
        )
