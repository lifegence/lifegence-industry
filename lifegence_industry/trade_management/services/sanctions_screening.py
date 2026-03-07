import frappe


@frappe.whitelist()
def screen_entity(entity_name, trade_shipment=None):
	"""Screen an entity against sanctions lists.

	Args:
		entity_name: Name to screen
		trade_shipment: Optional Trade Shipment to link the check record

	Returns:
		dict with keys: result, matches, check_name
	"""
	# Search local sanctions list entries
	matches = _search_sanctions_list(entity_name)

	# Determine result
	if not matches:
		result = "Clear"
	elif any(m.get("match_type") == "Exact" for m in matches):
		result = "Hit"
	else:
		result = "Possible Match"

	# Create compliance check record
	check_doc = frappe.get_doc({
		"doctype": "Trade Compliance Check",
		"check_type": "Sanctions Screening",
		"trade_shipment": trade_shipment,
		"check_date": frappe.utils.now(),
		"checked_entity": entity_name,
		"result": result,
		"matched_entries": [
			{
				"list_name": m["list_source"],
				"matched_name": m["entity_name"],
				"match_score": m.get("score", 0),
				"match_type": m.get("match_type", "Fuzzy"),
			}
			for m in matches
		],
	})
	check_doc.insert(ignore_permissions=True)

	return {
		"result": result,
		"matches": matches,
		"check_name": check_doc.name,
	}


def _search_sanctions_list(entity_name):
	"""Search sanctions list entries for matching names."""
	entity_lower = entity_name.lower().strip()

	# Exact match search
	exact = frappe.get_all(
		"Sanctions List Entry",
		filters={"entity_name": entity_name, "is_active": 1},
		fields=["entity_name", "entity_type", "list_source", "program"],
	)
	if exact:
		return [
			{**e, "match_type": "Exact", "score": 100}
			for e in exact
		]

	# Partial match (LIKE search)
	partial = frappe.get_all(
		"Sanctions List Entry",
		filters={"entity_name": ["like", f"%{entity_lower}%"], "is_active": 1},
		fields=["entity_name", "entity_type", "list_source", "program"],
		limit=10,
	)

	# Also check aliases field
	alias_matches = frappe.get_all(
		"Sanctions List Entry",
		filters={"aliases": ["like", f"%{entity_lower}%"], "is_active": 1},
		fields=["entity_name", "entity_type", "list_source", "program"],
		limit=10,
	)

	results = []
	seen = set()
	for entry in partial + alias_matches:
		if entry.entity_name not in seen:
			seen.add(entry.entity_name)
			results.append({**entry, "match_type": "Partial", "score": 70})

	return results


@frappe.whitelist()
def screen_shipment(trade_shipment):
	"""Screen all parties in a trade shipment.

	Returns:
		list of screening results for each party
	"""
	ts = frappe.get_doc("Trade Shipment", trade_shipment)
	results = []

	# Screen shipper
	if ts.shipper:
		shipper_name = frappe.db.get_value(ts.shipper_type, ts.shipper, "name")
		if shipper_name:
			results.append(screen_entity(shipper_name, trade_shipment))

	# Screen consignee
	if ts.consignee:
		consignee_name = frappe.db.get_value(ts.consignee_type, ts.consignee, "name")
		if consignee_name:
			results.append(screen_entity(consignee_name, trade_shipment))

	return results
