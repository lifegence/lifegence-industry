import frappe
from frappe.utils import today, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": "L/C Number", "fieldtype": "Link", "options": "Letter of Credit", "width": 150},
		{"fieldname": "lc_type", "label": "Type", "fieldtype": "Data", "width": 120},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 120},
		{"fieldname": "issuing_bank", "label": "Issuing Bank", "fieldtype": "Data", "width": 150},
		{"fieldname": "currency", "label": "Currency", "fieldtype": "Link", "options": "Currency", "width": 80},
		{"fieldname": "lc_amount", "label": "L/C Amount", "fieldtype": "Currency", "width": 130},
		{"fieldname": "drawn_amount", "label": "Drawn", "fieldtype": "Currency", "width": 120},
		{"fieldname": "balance", "label": "Balance", "fieldtype": "Currency", "width": 120},
		{"fieldname": "utilization_pct", "label": "Utilization %", "fieldtype": "Percent", "width": 100},
		{"fieldname": "expiry_date", "label": "Expiry", "fieldtype": "Date", "width": 100},
		{"fieldname": "days_to_expiry", "label": "Days Left", "fieldtype": "Int", "width": 80},
		{"fieldname": "trade_shipment", "label": "Shipment", "fieldtype": "Link", "options": "Trade Shipment", "width": 150},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters:
		if filters.get("status"):
			conditions.append("lc.status = %(status)s")
			values["status"] = filters["status"]
		if filters.get("issuing_bank"):
			conditions.append("lc.issuing_bank LIKE %(issuing_bank)s")
			values["issuing_bank"] = f"%{filters['issuing_bank']}%"

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	data = frappe.db.sql(
		f"""
		SELECT
			lc.name, lc.lc_type, lc.status, lc.issuing_bank,
			lc.currency, lc.lc_amount, lc.drawn_amount, lc.balance,
			lc.expiry_date, lc.trade_shipment
		FROM `tabLetter of Credit` lc
		WHERE {where_clause}
		ORDER BY lc.expiry_date ASC
		""",
		values=values,
		as_dict=True,
	)

	for row in data:
		if row.lc_amount:
			row["utilization_pct"] = (row.drawn_amount or 0) / row.lc_amount * 100
		else:
			row["utilization_pct"] = 0

		if row.expiry_date:
			row["days_to_expiry"] = date_diff(row.expiry_date, today())
		else:
			row["days_to_expiry"] = None

	return data
