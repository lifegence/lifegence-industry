# Copyright (c) 2026, Lifegence and contributors
# Public job search & listing page (/jobs)

import frappe
from frappe.utils import cint


def get_context(context):
	context.no_cache = 1
	context.nav_active = "jobs"

	form = frappe.form_dict
	keyword = (form.get("q") or "").strip()
	category = (form.get("category") or "").strip()
	location = (form.get("location") or "").strip()
	employment_type = (form.get("employment_type") or "").strip()
	status = (form.get("status") or "").strip()  # "" = all, "Open", "Closed"
	sort = (form.get("sort") or "recent").strip()
	page = max(cint(form.get("page")) or 1, 1)

	page_size = cint(frappe.db.get_single_value("Staffing Settings", "default_jobs_per_page")) or 20

	filters = {"publish": 1}
	if category:
		filters["job_category"] = category
	if location:
		filters["work_location"] = ["like", f"%{location}%"]
	if employment_type:
		filters["employment_type"] = employment_type
	if status in ("Open", "Closed"):
		filters["status"] = status

	or_filters = None
	if keyword:
		like = ["like", f"%{keyword}%"]
		or_filters = {
			"job_title": like,
			"work_location": like,
			"dispatch_client": like,
			"job_category": like,
		}

	order_by = {
		"recent": "modified desc",
		"pay_high": "pay_rate desc",
		"pay_low": "pay_rate asc",
	}.get(sort, "modified desc")
	# Keep open jobs above closed ones regardless of sort ('Open' > 'Closed')
	order_by = f"status desc, {order_by}"

	fields = [
		"name", "job_title", "route", "status", "dispatch_client", "job_category",
		"work_location", "employment_type", "pay_rate", "pay_rate_unit", "headcount",
		"description", "modified",
	]

	total = frappe.db.count("Dispatch Order", filters) if not or_filters else len(
		frappe.get_all("Dispatch Order", filters=filters, or_filters=or_filters, pluck="name")
	)

	jobs = frappe.get_all(
		"Dispatch Order",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by=order_by,
		start=(page - 1) * page_size,
		page_length=page_size,
	)

	for j in jobs:
		j["client_route"] = frappe.db.get_value("Dispatch Client", j.dispatch_client, "route")
		j["summary"] = _strip_html(j.get("description"))

	total_pages = max((total + page_size - 1) // page_size, 1)

	context.jobs = jobs
	context.total = total
	context.page = page
	context.total_pages = total_pages
	context.page_range = _page_range(page, total_pages)
	context.categories = frappe.get_all(
		"Job Category",
		filters={"disabled": 0},
		fields=["name", "category_name"],
		order_by="display_order asc, category_name asc",
	)
	context.locations = [
		r[0]
		for r in frappe.db.sql(
			"""select distinct work_location from `tabDispatch Order`
			where publish=1 and ifnull(work_location,'')!='' order by work_location"""
		)
	]
	context.filters = frappe._dict(
		q=keyword, category=category, location=location,
		employment_type=employment_type, status=status, sort=sort,
	)
	return context


def _strip_html(html):
	if not html:
		return ""
	import re

	text = re.sub(r"<[^>]+>", " ", html)
	text = re.sub(r"\s+", " ", text).strip()
	return text


def _page_range(page, total_pages, window=2):
	lo = max(1, page - window)
	hi = min(total_pages, page + window)
	return list(range(lo, hi + 1))
