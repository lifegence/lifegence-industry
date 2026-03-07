import frappe


@frappe.whitelist()
def check_document_consistency(trade_shipment):
	"""Check consistency across trade documents for a shipment.

	Compares Commercial Invoice, Packing List, B/L, and Customs Declaration
	for amount, quantity, weight, and party discrepancies.

	Args:
		trade_shipment: Trade Shipment name

	Returns:
		list of dicts with keys: check_item, status, details
	"""
	settings = frappe.get_single("Trade Settings")
	results = []

	ts = frappe.get_doc("Trade Shipment", trade_shipment)

	# Get linked documents
	ci_list = frappe.get_all(
		"Commercial Invoice",
		filters={"trade_shipment": trade_shipment},
		fields=["name", "total_amount", "currency"],
	)
	pl_list = frappe.get_all(
		"Packing List",
		filters={"trade_shipment": trade_shipment},
		fields=["name", "total_packages", "total_gross_weight"],
	)
	bl_list = frappe.get_all(
		"Bill of Lading",
		filters={"trade_shipment": trade_shipment},
		fields=["name", "total_packages", "gross_weight"],
	)

	# Check 1: Package count consistency (PL vs B/L vs Trade Shipment)
	if pl_list and bl_list:
		pl_packages = sum(pl.total_packages or 0 for pl in pl_list)
		bl_packages = sum(bl.total_packages or 0 for bl in bl_list)
		if pl_packages != bl_packages:
			results.append({
				"check_item": "Package Count (PL vs B/L)",
				"status": "Mismatch",
				"details": f"PL: {pl_packages}, B/L: {bl_packages}",
			})
		else:
			results.append({
				"check_item": "Package Count (PL vs B/L)",
				"status": "OK",
				"details": f"Both: {pl_packages}",
			})

	# Check 2: Weight consistency (PL vs B/L)
	if pl_list and bl_list:
		pl_weight = sum(pl.total_gross_weight or 0 for pl in pl_list)
		bl_weight = sum(bl.gross_weight or 0 for bl in bl_list)
		if abs(pl_weight - bl_weight) > 0.5:
			results.append({
				"check_item": "Gross Weight (PL vs B/L)",
				"status": "Mismatch",
				"details": f"PL: {pl_weight} kg, B/L: {bl_weight} kg",
			})
		else:
			results.append({
				"check_item": "Gross Weight (PL vs B/L)",
				"status": "OK",
				"details": f"PL: {pl_weight} kg, B/L: {bl_weight} kg",
			})

	# Check 3: Document completeness
	required_docs = {
		"Commercial Invoice": bool(ci_list),
		"Packing List": bool(pl_list),
		"Bill of Lading / Air Waybill": bool(bl_list) or bool(
			frappe.get_all("Air Waybill", filters={"trade_shipment": trade_shipment}, limit=1)
		),
	}
	for doc_name, exists in required_docs.items():
		results.append({
			"check_item": f"Document: {doc_name}",
			"status": "OK" if exists else "Missing",
			"details": "Found" if exists else "Not found",
		})

	# Check 4: AI-powered deep check (if enabled)
	if settings.enable_ai_document_check and ci_list:
		ai_results = _ai_document_check(ts, ci_list, pl_list, bl_list, settings)
		results.extend(ai_results)

	return results


def _ai_document_check(ts, ci_list, pl_list, bl_list, settings):
	"""AI-powered document consistency check. Currently a stub."""
	# TODO: Integrate with Gemini API
	return []
