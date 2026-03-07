# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


@frappe.whitelist()
def calculate_fee(encounter_id):
	"""Recalculate fee points for a Patient Encounter."""
	doc = frappe.get_doc("Patient Encounter", encounter_id)
	doc.calculate_totals()
	doc.save()
	frappe.db.commit()

	return {
		"encounter": doc.name,
		"total_points": doc.total_points,
		"total_amount": doc.total_amount,
		"copay_amount": doc.copay_amount,
		"insurance_claim_amount": doc.insurance_claim_amount,
	}


def on_encounter_submit(doc, method):
	"""Hook called when Patient Encounter is submitted via doc_events."""
	doc.calculate_totals()
