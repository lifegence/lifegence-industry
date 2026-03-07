import frappe


@frappe.whitelist()
def suggest_hs_code(item_name, description=None, material=None, usage=None):
	"""Suggest HS codes using AI based on item information.

	Args:
		item_name: Product name (Japanese or English)
		description: Product description
		material: Material composition
		usage: Intended use

	Returns:
		list of dicts with keys: hs_code, description, confidence, reasoning
	"""
	settings = frappe.get_single("Trade Settings")
	if not settings.enable_ai_hs_suggestion:
		frappe.throw("AI HS Code suggestion is not enabled in Trade Settings.")

	prompt = _build_hs_prompt(item_name, description, material, usage)
	result = _call_ai(prompt, settings)

	return result or []


def _build_hs_prompt(item_name, description=None, material=None, usage=None):
	"""Build the prompt for HS code suggestion."""
	parts = [
		f"Product: {item_name}",
	]
	if description:
		parts.append(f"Description: {description}")
	if material:
		parts.append(f"Material: {material}")
	if usage:
		parts.append(f"Usage: {usage}")

	product_info = "\n".join(parts)

	return f"""You are an expert in customs tariff classification (HS codes).
Based on the following product information, suggest the top 3 most likely HS codes.

{product_info}

For each suggestion, provide:
1. HS Code (6-digit international + 4-digit national for Japan)
2. Description of the tariff heading
3. Confidence score (0-100%)
4. Brief reasoning for the classification

Respond in JSON format:
[
  {{"hs_code": "8542.31-000", "description": "...", "confidence": 92, "reasoning": "..."}},
  ...
]"""


def _call_ai(prompt, settings):
	"""Call AI API for HS code suggestion. Currently a stub."""
	# TODO: Integrate with Gemini API via Company OS AI Settings
	# For now, return empty to indicate no AI response
	frappe.log_error(
		title="AI HS Suggestion",
		message="AI integration not yet configured. Enable Gemini API in Company OS AI Settings.",
	)
	return []
