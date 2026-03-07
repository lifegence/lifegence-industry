# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Trigger event analysis: counts by type with severity aggregation.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate


@frappe.whitelist()
def get_trigger_analysis(period: str = "month", department: str = None):
    """
    Get analysis of trigger events

    Args:
        period: Time period (week, month, quarter)
        department: Optional department filter

    Returns:
        dict: Trigger analysis with counts by type
    """
    roles = frappe.get_roles()
    if "Mind Analyzer Manager" not in roles and "System Manager" not in roles:
        frappe.throw(_("You don't have permission to view trigger reports"))

    today = getdate()
    if period == "week":
        start_date = add_days(today, -7)
    elif period == "quarter":
        start_date = add_days(today, -90)
    else:
        start_date = add_days(today, -30)

    # Build filters
    filters = {}
    if department:
        employees = frappe.get_all(
            "Employee",
            filters={"department": department, "status": "Active"},
            fields=["user_id"]
        )
        user_ids = [e.user_id for e in employees if e.user_id]

        sessions = frappe.get_all(
            "Voice Analysis Session",
            filters={
                "user": ["in", user_ids],
                "start_time": [">=", start_date]
            },
            fields=["name"]
        )
        session_names = [s.name for s in sessions]
        filters["session"] = ["in", session_names]
    else:
        # Get sessions in date range
        sessions = frappe.get_all(
            "Voice Analysis Session",
            filters={"start_time": [">=", start_date]},
            fields=["name"]
        )
        session_names = [s.name for s in sessions]
        filters["session"] = ["in", session_names]

    if not session_names:
        return {
            "period": period,
            "department": department,
            "total_triggers": 0,
            "by_type": {}
        }

    # Get all triggers
    triggers = frappe.get_all(
        "Voice Trigger Event",
        filters=filters,
        fields=["trigger_type", "severity", "timestamp"]
    )

    # Count by type
    by_type = {}
    for trigger in triggers:
        t = trigger.trigger_type
        if t not in by_type:
            by_type[t] = {"count": 0, "total_severity": 0}
        by_type[t]["count"] += 1
        by_type[t]["total_severity"] += trigger.severity or 0

    # Calculate averages
    for t in by_type:
        if by_type[t]["count"] > 0:
            by_type[t]["avg_severity"] = round(
                by_type[t]["total_severity"] / by_type[t]["count"], 3
            )
        del by_type[t]["total_severity"]

    # Sort by count
    sorted_types = sorted(by_type.items(), key=lambda x: x[1]["count"], reverse=True)

    return {
        "period": period,
        "department": department,
        "start_date": str(start_date),
        "end_date": str(today),
        "total_triggers": len(triggers),
        "total_sessions": len(session_names),
        "triggers_per_session": round(len(triggers) / len(session_names), 2) if session_names else 0,
        "by_type": dict(sorted_types)
    }
