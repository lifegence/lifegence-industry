# Copyright (c) 2026, Lifegence and contributors
# Public job application form (/jobs/apply?job=<Dispatch Order>)

import frappe

DEFAULT_POLICY = """
<h3>1. 個人情報の収集と利用目的</h3>
<p>当社は、応募手続きにおいて取得した氏名・連絡先・経歴等の個人情報を、応募いただいたお仕事の選考、および適切なお仕事のご紹介の目的にのみ利用します。</p>
<h3>2. 第三者への提供</h3>
<p>取得した個人情報は、派遣先企業への紹介に必要な範囲を除き、ご本人の同意なく第三者に提供することはありません。</p>
<h3>3. 安全管理措置</h3>
<p>当社は、個人情報の漏洩・滅失・毀損の防止その他の安全管理のために必要かつ適切な措置を講じます。</p>
<h3>4. 開示・訂正・削除のご請求</h3>
<p>ご本人からの個人情報の開示・訂正・削除のご請求には、法令に従い適切に対応します。</p>
<p>本フォームを送信することで、上記の個人情報の取り扱いに同意いただいたものとみなします。</p>
"""


def get_context(context):
	context.no_cache = 1
	context.nav_active = "jobs"

	job_name = frappe.form_dict.get("job")
	context.job = None
	if job_name:
		job = frappe.db.get_value(
			"Dispatch Order",
			job_name,
			["name", "job_title", "dispatch_client", "status", "publish", "work_location", "job_category"],
			as_dict=True,
		)
		if job and job.publish:
			context.job = job
			context.is_closed = job.status == "Closed"

	policy = frappe.db.get_single_value("Staffing Settings", "privacy_policy")
	context.privacy_policy = policy or DEFAULT_POLICY
	return context
