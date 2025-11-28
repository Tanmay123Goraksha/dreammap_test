# TODO: Fix Low Monthly Saving in AI Response

## Steps to Complete
- [x] Update `agent.py` to include `tools=[get_real_world_cost_tool]` in the `GenerateContentConfig` for the main AI call.
- [x] Modify the prompt in `generate_dynamic_roadmap` to instruct the AI to use the `get_real_world_cost` tool for accurate cost estimates in INR.
- [x] Add calculation for `savingPercentage` in the main response: `savingPercentage = round((monthly_saving / user_income) * 100, 2) if user_income > 0 else 0.0`.
- [x] Test the API with the bike input to verify higher monthly savings and correct saving percentage.
