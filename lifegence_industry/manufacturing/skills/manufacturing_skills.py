# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

"""Manufacturing AI agent skills.

Read-only skills that let the chat agent answer questions about
production, orders, inventory, procurement, and quality — the core
loop of a manufacturing tenant (e.g. the demo-factory demo story).
"""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from lifegence_agent.skills.registry import register_skill

OPEN_WO_STATUSES = ["Not Started", "In Process", "Draft"]


def _has_column(doctype: str, column: str) -> bool:
	try:
		return column in frappe.db.get_table_columns(doctype)
	except Exception:
		return False


def _work_order_rows(filters=None, limit=50):
	rows = frappe.get_all(
		"Work Order",
		filters=filters or {},
		fields=[
			"name", "production_item", "item_name", "qty", "produced_qty",
			"status", "planned_start_date", "planned_end_date",
			"expected_delivery_date", "bom_no",
		],
		order_by="planned_start_date asc",
		limit_page_length=limit,
	)
	today = getdate(nowdate())
	for r in rows:
		r["progress_pct"] = round(flt(r.produced_qty) / flt(r.qty) * 100, 1) if flt(r.qty) else 0
		due = r.get("expected_delivery_date") or r.get("planned_end_date")
		r["is_delayed"] = bool(
			due and getdate(due) < today and r.status not in ("Completed", "Stopped", "Closed")
		)
	return rows


@register_skill(
	skill_name="mfg_production_status",
	description=(
		"Get manufacturing production status: work order list with progress "
		"(produced vs planned qty), status counts, and delayed work orders. "
		"Use when the user asks about 生産状況 / production progress / "
		"作業指示 / whether manufacturing is on schedule."
	),
	parameters={
		"type": "object",
		"properties": {
			"status": {
				"type": "string",
				"description": "Filter by Work Order status: Not Started, In Process, Completed, Stopped, Closed. Empty for all.",
			},
			"item_code": {
				"type": "string",
				"description": "Filter by production item code (e.g. 'RSX-100'). Empty for all items.",
			},
			"limit": {"type": "integer", "description": "Max work orders to return (default 20)"},
		},
		"required": [],
	},
	risk_level="Low",
	skill_type="Custom",
)
def mfg_production_status(status=None, item_code=None, limit=20):
	"""Summarize work orders: progress, status distribution, delays."""
	filters = {"docstatus": ["<", 2]}
	if status:
		filters["status"] = status
	if item_code:
		filters["production_item"] = item_code

	rows = _work_order_rows(filters, limit=min(int(limit or 20), 50))

	by_status = {}
	for r in frappe.db.sql(
		"""
		SELECT status, COUNT(name) AS count, SUM(qty) AS total_qty,
			SUM(produced_qty) AS produced_qty
		FROM `tabWork Order`
		WHERE docstatus < 2
		GROUP BY status
		""",
		as_dict=True,
	):
		by_status[r.status] = {
			"count": r.count,
			"total_qty": flt(r.total_qty),
			"produced_qty": flt(r.produced_qty),
		}

	return {
		"success": True,
		"summary_by_status": by_status,
		"work_orders": rows,
		"delayed": [r for r in rows if r["is_delayed"]],
	}


@register_skill(
	skill_name="mfg_order_delivery_status",
	description=(
		"Check sales orders and delivery schedule: open order backlog, "
		"delivery dates per customer/item, today's and upcoming shipments, "
		"and overdue deliveries. Use for 受注状況 / 納期 / 出荷予定 / "
		"'when can we deliver X' questions."
	),
	parameters={
		"type": "object",
		"properties": {
			"customer": {
				"type": "string",
				"description": "Filter by customer name (partial match OK). Empty for all.",
			},
			"item_code": {"type": "string", "description": "Filter by item code. Empty for all."},
			"days_ahead": {
				"type": "integer",
				"description": "Window in days for upcoming deliveries (default 7)",
			},
		},
		"required": [],
	},
	risk_level="Low",
	skill_type="Custom",
)
def mfg_order_delivery_status(customer=None, item_code=None, days_ahead=7):
	"""Open sales order backlog and delivery schedule."""
	conditions = ["so.docstatus = 1", "so.status not in ('Completed', 'Closed', 'Cancelled')"]
	params = {}
	if customer:
		conditions.append("so.customer_name like %(customer)s")
		params["customer"] = f"%{customer}%"
	if item_code:
		conditions.append("soi.item_code = %(item_code)s")
		params["item_code"] = item_code

	lines = frappe.db.sql(
		f"""
		SELECT so.name AS sales_order, so.customer_name, so.transaction_date,
			soi.item_code, soi.item_name, soi.qty, soi.delivered_qty,
			soi.delivery_date, so.status
		FROM `tabSales Order` so
		JOIN `tabSales Order Item` soi ON soi.parent = so.name
		WHERE {' AND '.join(conditions)}
		ORDER BY soi.delivery_date asc
		LIMIT 100
		""",
		params,
		as_dict=True,
	)

	today = getdate(nowdate())
	horizon = getdate(add_days(nowdate(), int(days_ahead or 7)))
	backlog, overdue, upcoming = [], [], []
	for ln in lines:
		ln["pending_qty"] = flt(ln.qty) - flt(ln.delivered_qty)
		if ln["pending_qty"] <= 0:
			continue
		backlog.append(ln)
		if ln.delivery_date and getdate(ln.delivery_date) < today:
			overdue.append(ln)
		elif ln.delivery_date and today <= getdate(ln.delivery_date) <= horizon:
			upcoming.append(ln)

	total_backlog_qty = sum(ln["pending_qty"] for ln in backlog)
	return {
		"success": True,
		"open_order_lines": backlog[:50],
		"overdue_deliveries": overdue,
		"upcoming_deliveries": upcoming,
		"totals": {
			"open_lines": len(backlog),
			"pending_qty": total_backlog_qty,
			"overdue_lines": len(overdue),
		},
	}


@register_skill(
	skill_name="mfg_inventory_check",
	description=(
		"Check stock levels and material availability. Given an item and "
		"quantity, explodes the default BOM and reports which raw materials "
		"are short. Without qty, returns current warehouse stock. Use for "
		"在庫確認 / 資材は足りるか / material shortage questions."
	),
	parameters={
		"type": "object",
		"properties": {
			"item_code": {
				"type": "string",
				"description": "Item code to check (e.g. 'RSX-100'). Empty lists low/negative stock items.",
			},
			"qty_to_make": {
				"type": "integer",
				"description": "Planned production qty. If given with item_code, checks BOM material availability.",
			},
		},
		"required": [],
	},
	risk_level="Low",
	skill_type="Custom",
)
def mfg_inventory_check(item_code=None, qty_to_make=None):
	"""Warehouse stock and BOM-exploded material shortage check."""

	def stock_of(code):
		bins = frappe.get_all(
			"Bin",
			filters={"item_code": code},
			fields=["warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty"],
		)
		return bins, sum(flt(b.actual_qty) for b in bins)

	result = {"success": True}

	if item_code:
		bins, total = stock_of(item_code)
		result["item_code"] = item_code
		result["item_name"] = frappe.db.get_value("Item", item_code, "item_name")
		result["warehouses"] = bins
		result["total_actual_qty"] = total

		if qty_to_make:
			bom = frappe.db.get_value(
				"BOM", {"item": item_code, "is_default": 1, "is_active": 1, "docstatus": 1}, "name"
			)
			if not bom:
				result["bom_check"] = f"No default BOM found for {item_code}"
			else:
				bom_qty = flt(frappe.db.get_value("BOM", bom, "quantity")) or 1
				materials = frappe.get_all(
					"BOM Item",
					filters={"parent": bom},
					fields=["item_code", "item_name", "stock_qty"],
				)
				shortages, availability = [], []
				for m in materials:
					required = flt(m.stock_qty) / bom_qty * flt(qty_to_make)
					_, on_hand = stock_of(m.item_code)
					row = {
						"item_code": m.item_code,
						"item_name": m.item_name,
						"required_qty": round(required, 2),
						"on_hand_qty": on_hand,
						"shortage_qty": round(max(required - on_hand, 0), 2),
					}
					availability.append(row)
					if row["shortage_qty"] > 0:
						shortages.append(row)
				result["bom"] = bom
				result["qty_to_make"] = qty_to_make
				result["materials"] = availability
				result["shortages"] = shortages
				result["all_materials_available"] = not shortages
	else:
		low = frappe.db.sql(
			"""
			SELECT b.item_code, i.item_name, SUM(b.actual_qty) AS actual_qty,
				SUM(b.reserved_qty) AS reserved_qty, SUM(b.ordered_qty) AS ordered_qty
			FROM `tabBin` b
			JOIN `tabItem` i ON i.name = b.item_code
			GROUP BY b.item_code
			HAVING SUM(b.actual_qty) <= 10
			ORDER BY actual_qty asc
			LIMIT 30
			""",
			as_dict=True,
		)
		result["low_stock_items"] = low

	return result


@register_skill(
	skill_name="mfg_procurement_status",
	description=(
		"Check purchasing status: open purchase orders, expected receipt "
		"dates, overdue (delayed) supplier deliveries, and recent receipts. "
		"Use for 発注状況 / 入荷予定 / 未入荷 / supplier delay questions."
	),
	parameters={
		"type": "object",
		"properties": {
			"supplier": {
				"type": "string",
				"description": "Filter by supplier name (partial match). Empty for all.",
			},
			"limit": {"type": "integer", "description": "Max purchase orders to return (default 20)"},
		},
		"required": [],
	},
	risk_level="Low",
	skill_type="Custom",
)
def mfg_procurement_status(supplier=None, limit=20):
	"""Open POs, overdue receipts, and recent purchase receipts."""
	conditions = ["po.docstatus = 1", "po.status not in ('Completed', 'Closed', 'Cancelled')"]
	params = {}
	if supplier:
		conditions.append("po.supplier_name like %(supplier)s")
		params["supplier"] = f"%{supplier}%"

	pos = frappe.db.sql(
		f"""
		SELECT po.name, po.supplier_name, po.transaction_date, po.schedule_date,
			po.status, po.grand_total, po.per_received
		FROM `tabPurchase Order` po
		WHERE {' AND '.join(conditions)}
		ORDER BY po.schedule_date asc
		LIMIT %(limit)s
		""",
		{**params, "limit": min(int(limit or 20), 50)},
		as_dict=True,
	)

	today = getdate(nowdate())
	for po in pos:
		po["is_overdue"] = bool(
			po.schedule_date and getdate(po.schedule_date) < today and flt(po.per_received) < 100
		)

	recent_receipts = frappe.get_all(
		"Purchase Receipt",
		filters={"docstatus": 1},
		fields=["name", "supplier_name", "posting_date", "grand_total", "status"],
		order_by="posting_date desc",
		limit_page_length=5,
	)

	return {
		"success": True,
		"open_purchase_orders": pos,
		"overdue_purchase_orders": [p for p in pos if p["is_overdue"]],
		"recent_receipts": recent_receipts,
		"totals": {
			"open_count": len(pos),
			"overdue_count": sum(1 for p in pos if p["is_overdue"]),
			"open_amount": sum(flt(p.grand_total) for p in pos),
		},
	}


@register_skill(
	skill_name="mfg_quality_summary",
	description=(
		"Summarize quality inspections: accepted/rejected counts by "
		"inspection type, rejection rate per item, and recent rejections. "
		"Use for 品質状況 / 不良率 / 検査結果 / quality trend questions."
	),
	parameters={
		"type": "object",
		"properties": {
			"days": {
				"type": "integer",
				"description": "Lookback window in days (default 30)",
			},
			"item_code": {"type": "string", "description": "Filter by item code. Empty for all."},
		},
		"required": [],
	},
	risk_level="Low",
	skill_type="Custom",
)
def mfg_quality_summary(days=30, item_code=None):
	"""Quality inspection pass/fail summary and rejection details."""
	since = add_days(nowdate(), -int(days or 30))
	filters = {"docstatus": ["<", 2], "report_date": [">=", since]}
	if item_code:
		filters["item_code"] = item_code

	inspections = frappe.get_all(
		"Quality Inspection",
		filters=filters,
		fields=[
			"name", "report_date", "inspection_type", "item_code", "item_name",
			"sample_size", "status", "reference_type", "reference_name",
		],
		order_by="report_date desc",
		limit_page_length=200,
	)

	by_type, by_item = {}, {}
	for qi in inspections:
		t = by_type.setdefault(qi.inspection_type or "Other", {"accepted": 0, "rejected": 0})
		i = by_item.setdefault(qi.item_code, {"item_name": qi.item_name, "accepted": 0, "rejected": 0})
		key = "accepted" if qi.status == "Accepted" else "rejected"
		t[key] += 1
		i[key] += 1

	for i in by_item.values():
		total = i["accepted"] + i["rejected"]
		i["rejection_rate_pct"] = round(i["rejected"] / total * 100, 1) if total else 0

	total = len(inspections)
	rejected = sum(1 for q in inspections if q.status != "Accepted")
	return {
		"success": True,
		"period_days": days,
		"totals": {
			"inspections": total,
			"accepted": total - rejected,
			"rejected": rejected,
			"rejection_rate_pct": round(rejected / total * 100, 1) if total else 0,
		},
		"by_inspection_type": by_type,
		"by_item": by_item,
		"recent_rejections": [q for q in inspections if q.status != "Accepted"][:10],
	}


@register_skill(
	skill_name="mfg_daily_briefing",
	description=(
		"Morning briefing for factory managers: one-shot cross-functional "
		"summary of production progress, delayed work orders, today's and "
		"this week's deliveries, quality alerts, new sales orders, and "
		"documents waiting for approval. Use for 今日の状況 / 朝会 / "
		"daily briefing / 'summarize today' requests."
	),
	parameters={
		"type": "object",
		"properties": {
			"days_ahead": {
				"type": "integer",
				"description": "Window in days for upcoming deliveries (default 7)",
			},
		},
		"required": [],
	},
	risk_level="Low",
	skill_type="Custom",
)
def mfg_daily_briefing(days_ahead=7):
	"""Cross-functional daily briefing for the factory director."""
	briefing = {"success": True, "date": nowdate()}

	# Production
	try:
		wo = mfg_production_status(limit=50)
		in_process = wo["summary_by_status"].get("In Process", {})
		briefing["production"] = {
			"summary_by_status": wo["summary_by_status"],
			"in_process_count": in_process.get("count", 0),
			"delayed_work_orders": wo["delayed"][:5],
		}
	except Exception as e:
		briefing["production"] = {"error": str(e)}

	# Deliveries
	try:
		dl = mfg_order_delivery_status(days_ahead=days_ahead)
		briefing["deliveries"] = {
			"upcoming": dl["upcoming_deliveries"][:5],
			"overdue": dl["overdue_deliveries"][:5],
			"backlog_totals": dl["totals"],
		}
	except Exception as e:
		briefing["deliveries"] = {"error": str(e)}

	# Quality (last 7 days)
	try:
		q = mfg_quality_summary(days=7)
		briefing["quality"] = {
			"totals": q["totals"],
			"recent_rejections": q["recent_rejections"][:3],
		}
	except Exception as e:
		briefing["quality"] = {"error": str(e)}

	# New sales orders (last 7 days)
	try:
		briefing["new_orders"] = frappe.get_all(
			"Sales Order",
			filters={"docstatus": 1, "transaction_date": [">=", add_days(nowdate(), -7)]},
			fields=["name", "customer_name", "transaction_date", "grand_total", "delivery_date"],
			order_by="transaction_date desc",
			limit_page_length=5,
		)
	except Exception as e:
		briefing["new_orders"] = {"error": str(e)}

	# Procurement snapshot
	try:
		po = mfg_procurement_status(limit=50)
		briefing["procurement"] = {
			"totals": po["totals"],
			"overdue": po["overdue_purchase_orders"][:3],
		}
	except Exception as e:
		briefing["procurement"] = {"error": str(e)}

	# Pending approvals (workflow-enabled docs in a requesting state)
	pending = []
	try:
		for doctype in ("Material Request", "Purchase Order", "Quality Inspection"):
			if not _has_column(doctype, "workflow_state"):
				continue
			rows = frappe.get_all(
				doctype,
				filters={
					"docstatus": 0,
					"workflow_state": ["in", frappe.get_all(
						"Workflow State",
						filters={"name": ["like", "Pending%"]},
						pluck="name",
					) + ["承認待ち"]],
				},
				fields=["name", "workflow_state", "modified"],
				limit_page_length=5,
			)
			for r in rows:
				r["doctype"] = doctype
			pending.extend(rows)
	except Exception:
		pass
	briefing["pending_approvals"] = pending[:10]

	return briefing
