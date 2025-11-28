# TODO: Fix Low Monthly Saving in AI Response

## Steps to Complete
- [x] Update `agent.py` to include `tools=[get_real_world_cost_tool]` in the `GenerateContentConfig` for the main AI call.
- [x] Modify the prompt in `generate_dynamic_roadmap` to instruct the AI to use the `get_real_world_cost` tool for accurate cost estimates in INR.
- [x] Add calculation for `savingPercentage` in the main response: `savingPercentage = round((monthly_saving / user_income) * 100, 2) if user_income > 0 else 0.0`.
- [x] Test the API with the bike input to verify higher monthly savings and correct saving percentage.

---

# User Comparison Feature

## Completed
- [x] Created `comparison_agent.py` with AI-powered user comparison logic
- [x] Added `UserComparisonInsights` model to `models.py`
- [x] Implemented `/api/compare-users` endpoint in `main.py`
- [x] Added CSV transaction parsing and analysis
- [x] Created test script `test_comparison.py`
- [x] Added comprehensive documentation in `COMPARISON_FEATURE.md`

## Features Implemented
- Job profile comparison
- Savings pattern analysis
- Spending behavior insights
- **Data-driven recommendations with specific amounts and percentages**
- Unnecessary expense detection with quantified targets
- Peer benchmarking with specific insights
- Category-level spending breakdown with variance analysis
- Savings gap calculation with timeline projections
- Robust fallback logic with calculated metrics
