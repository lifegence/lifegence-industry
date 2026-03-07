# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Monthly report API endpoints: list, detail, generation, comparison.
"""

import json

import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, add_months

from lifegence_industry.mind_analyzer.api.session import has_analyzer_access


@frappe.whitelist()
def get_my_monthly_reports(limit: int = 12) -> dict:
    """
    Get current user's monthly reports

    Args:
        limit: Maximum number of reports to return

    Returns:
        dict: List of reports with summary info
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    user = frappe.session.user

    reports = frappe.get_all(
        "Monthly Report",
        filters={"user": user},
        fields=[
            "name", "report_month", "status", "overall_score",
            "overall_trend", "total_sessions", "generated_at"
        ],
        order_by="report_month desc",
        limit=int(limit)
    )

    # Format for display
    for report in reports:
        report["report_month_display"] = getdate(report.report_month).strftime("%Y年%m月")
        report["overall_score"] = round(report.overall_score or 0, 1)

    return {
        "success": True,
        "reports": reports
    }


@frappe.whitelist()
def get_monthly_report_detail(report_name: str = None, report_month: str = None) -> dict:
    """
    Get detailed monthly report data

    Args:
        report_name: Report document name (e.g., MR-2026-01-user@example.com)
        report_month: Or specify month (YYYY-MM-DD) to get current user's report

    Returns:
        dict: Full report data formatted for display
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    user = frappe.session.user

    if report_name:
        report = frappe.get_doc("Monthly Report", report_name)
        # Check permission
        if report.user != user and not frappe.has_permission("Monthly Report", "read", report):
            frappe.throw(_("You don't have permission to view this report"))
    elif report_month:
        first_day = get_first_day(getdate(report_month))
        report_name = frappe.db.get_value("Monthly Report", {
            "user": user,
            "report_month": first_day
        })
        if not report_name:
            return {
                "success": False,
                "message": _("Report not found for this month")
            }
        report = frappe.get_doc("Monthly Report", report_name)
    else:
        frappe.throw(_("Please specify report_name or report_month"))

    return {
        "success": True,
        "report": report.as_dict_for_report()
    }


@frappe.whitelist()
def get_latest_monthly_report() -> dict:
    """
    Get the most recent monthly report for current user

    Returns:
        dict: Latest report data or message if no report exists
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    user = frappe.session.user

    latest = frappe.get_all(
        "Monthly Report",
        filters={"user": user, "status": "Published"},
        fields=["name"],
        order_by="report_month desc",
        limit=1
    )

    if not latest:
        return {
            "success": False,
            "message": _("No reports found")
        }

    report = frappe.get_doc("Monthly Report", latest[0].name)
    return {
        "success": True,
        "report": report.as_dict_for_report()
    }


@frappe.whitelist()
def generate_monthly_report(report_month: str = None) -> dict:
    """
    Generate a monthly report for current user

    Args:
        report_month: Month to generate (YYYY-MM-DD, default: previous month)

    Returns:
        dict: Generated report info
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    from lifegence_industry.mind_analyzer.services.report_generator import ReportGeneratorService

    user = frappe.session.user

    if not report_month:
        # Default to previous month
        report_month = get_first_day(add_months(getdate(), -1))

    # Check if report already exists
    first_day = get_first_day(getdate(report_month))
    existing = frappe.db.exists("Monthly Report", {
        "user": user,
        "report_month": first_day
    })

    if existing:
        return {
            "success": False,
            "message": _("Report for this month already exists"),
            "report_name": existing
        }

    try:
        generator = ReportGeneratorService()
        report = generator.generate_report(user, str(report_month))

        return {
            "success": True,
            "message": _("Report generated successfully"),
            "report_name": report.name,
            "report": report.as_dict_for_report()
        }
    except Exception as e:
        frappe.log_error(f"Report generation failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_available_report_months() -> dict:
    """
    Get list of months that have analysis data (for report generation)

    Returns:
        dict: List of months with session counts
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    user = frappe.session.user

    # Get months with completed sessions
    months_data = frappe.db.sql("""
        SELECT
            DATE_FORMAT(start_time, '%%Y-%%m-01') as month,
            COUNT(*) as session_count
        FROM `tabVoice Analysis Session`
        WHERE user = %s AND status = 'Completed'
        GROUP BY DATE_FORMAT(start_time, '%%Y-%%m-01')
        ORDER BY month DESC
        LIMIT 12
    """, (user,), as_dict=True)

    # Check which months already have reports
    for month_data in months_data:
        first_day = getdate(month_data["month"])
        month_data["month_display"] = first_day.strftime("%Y年%m月")
        month_data["has_report"] = bool(frappe.db.exists("Monthly Report", {
            "user": user,
            "report_month": first_day
        }))

    return {
        "success": True,
        "months": months_data
    }


@frappe.whitelist()
def compare_monthly_reports(report_names: str) -> dict:
    """
    Compare multiple monthly reports (for trend analysis)

    Args:
        report_names: JSON array of report names to compare

    Returns:
        dict: Comparison data
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    user = frappe.session.user
    names = json.loads(report_names) if isinstance(report_names, str) else report_names

    if len(names) < 2:
        frappe.throw(_("Please select at least 2 reports to compare"))

    reports_data = []
    for name in names:
        report = frappe.get_doc("Monthly Report", name)
        if report.user != user and not frappe.has_permission("Monthly Report", "read", report):
            continue
        reports_data.append({
            "name": report.name,
            "month": str(report.report_month),
            "month_display": getdate(report.report_month).strftime("%Y年%m月"),
            "overall_score": report.overall_score,
            "avg_stress_load": report.avg_stress_load,
            "avg_stability": report.avg_stability,
            "avg_ps_score": report.avg_ps_score,
            "total_triggers": report.total_triggers,
            "total_sessions": report.total_sessions,
        })

    # Sort by month
    reports_data.sort(key=lambda x: x["month"])

    # Calculate changes
    changes = {}
    if len(reports_data) >= 2:
        first = reports_data[0]
        last = reports_data[-1]
        changes = {
            "overall_score": _calc_percent_change(first["overall_score"], last["overall_score"]),
            "avg_stress_load": _calc_percent_change(first["avg_stress_load"], last["avg_stress_load"]),
            "avg_stability": _calc_percent_change(first["avg_stability"], last["avg_stability"]),
            "avg_ps_score": _calc_percent_change(first["avg_ps_score"], last["avg_ps_score"]),
        }

    return {
        "success": True,
        "reports": reports_data,
        "changes": changes
    }


def _calc_percent_change(old_val, new_val):
    """Calculate percentage change"""
    if old_val is None or new_val is None:
        return None
    if old_val == 0:
        return None
    return round((new_val - old_val) / old_val * 100, 1)
