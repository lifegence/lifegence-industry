# Copyright (c) 2026, Lifegence and contributors
# Public staffing portal API (guest-accessible).

import hashlib

import frappe
from frappe import _


def _policy_version():
	policy = frappe.db.get_single_value("Staffing Settings", "privacy_policy") or ""
	return hashlib.md5(policy.encode("utf-8")).hexdigest()[:12]


@frappe.whitelist(allow_guest=True)
def submit_application(
	dispatch_order,
	applicant_name,
	email_id,
	phone_number,
	privacy_consent,
	name_kana=None,
	birth_date=None,
	postal_code=None,
	address=None,
	desired_note=None,
):
	"""Create a Job Application from the public site. Requires explicit consent."""
	consent = str(privacy_consent).lower() in ("1", "true", "on", "yes")
	if not consent:
		frappe.throw(_("個人情報の取り扱いへの同意が必要です。"))

	order = frappe.db.get_value(
		"Dispatch Order", dispatch_order, ["name", "publish", "status", "job_title"], as_dict=True
	)
	if not order or not order.publish:
		frappe.throw(_("対象のお仕事が見つかりません。"))
	if order.status == "Closed":
		frappe.throw(_("このお仕事の募集は終了しています。"))

	doc = frappe.get_doc(
		{
			"doctype": "Job Application",
			"dispatch_order": dispatch_order,
			"applicant_name": applicant_name,
			"name_kana": name_kana,
			"email_id": email_id,
			"phone_number": phone_number,
			"birth_date": birth_date or None,
			"postal_code": postal_code,
			"address": address,
			"desired_note": desired_note,
			"privacy_consent": 1,
			"consent_datetime": frappe.utils.now_datetime(),
			"policy_version": _policy_version(),
			"source": "公開サイト",
			"status": "新規",
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"name": doc.name, "job_title": order.job_title}
