# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Dashboard summary and recent triggers for the current user.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from lifegence_industry.mind_analyzer.api.session import has_analyzer_access


@frappe.whitelist()
def get_summary(days: int = 30):
    """
    Get summary statistics for the dashboard

    Args:
        days: Number of days to include (default 30)

    Returns:
        dict: Summary with total sessions, avg stress, avg PS, total triggers
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    user = frappe.session.user
    start_date = add_days(getdate(), -days)

    # Get sessions for current user
    sessions = frappe.get_all(
        "Voice Analysis Session",
        filters={
            "user": user,
            "status": "Completed",
            "start_time": [">=", start_date]
        },
        fields=["name", "mode", "avg_stress_load", "avg_ps_score", "trigger_count"]
    )

    # Calculate averages
    individual_sessions = [s for s in sessions if s.mode == "Individual"]
    meeting_sessions = [s for s in sessions if s.mode == "Meeting"]

    avg_stress = None
    if individual_sessions:
        stress_values = [s.avg_stress_load for s in individual_sessions if s.avg_stress_load]
        if stress_values:
            avg_stress = sum(stress_values) / len(stress_values)

    avg_ps = None
    if meeting_sessions:
        ps_values = [s.avg_ps_score for s in meeting_sessions if s.avg_ps_score]
        if ps_values:
            avg_ps = sum(ps_values) / len(ps_values)

    total_triggers = sum(s.trigger_count or 0 for s in sessions)

    return {
        "total_sessions": len(sessions),
        "individual_sessions": len(individual_sessions),
        "meeting_sessions": len(meeting_sessions),
        "avg_stress": round(avg_stress, 3) if avg_stress else None,
        "avg_ps": round(avg_ps, 3) if avg_ps else None,
        "total_triggers": total_triggers
    }


@frappe.whitelist()
def get_recent_triggers(limit: int = 10):
    """
    Get recent trigger events for the current user

    Args:
        limit: Maximum number of triggers to return

    Returns:
        list: Recent triggers with type, severity, evidence, timestamp
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to view Mind Analyzer"))

    user = frappe.session.user

    # Get user's sessions
    sessions = frappe.get_all(
        "Voice Analysis Session",
        filters={"user": user},
        fields=["name"]
    )

    if not sessions:
        return []

    session_names = [s.name for s in sessions]

    # Get recent triggers
    triggers = frappe.get_all(
        "Voice Trigger Event",
        filters={"session": ["in", session_names]},
        fields=["trigger_type", "severity", "evidence", "timestamp", "session"],
        order_by="timestamp desc",
        limit=limit
    )

    return triggers
