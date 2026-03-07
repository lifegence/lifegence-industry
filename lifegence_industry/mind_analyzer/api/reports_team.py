# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Team analysis: manager's direct reports and organization-wide team metrics.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate


@frappe.whitelist()
def get_team_analysis(manager: str = None):
    """
    Get team analysis for a manager's direct reports

    Args:
        manager: Manager's employee ID (defaults to current user's employee)

    Returns:
        dict: Team analysis with individual metrics
    """
    roles = frappe.get_roles()
    if "Mind Analyzer Manager" not in roles and "System Manager" not in roles:
        frappe.throw(_("You don't have permission to view team reports"))

    # Get manager's employee record
    if not manager:
        manager = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user},
            "name"
        )

    if not manager:
        frappe.throw(_("Employee record not found"))

    # Get direct reports
    reports = frappe.get_all(
        "Employee",
        filters={"reports_to": manager, "status": "Active"},
        fields=["name", "user_id", "employee_name", "designation"]
    )

    if not reports:
        return {
            "manager": manager,
            "team_size": 0,
            "members": []
        }

    # Get last 30 days data for each team member
    start_date = add_days(getdate(), -30)
    team_data = []

    for employee in reports:
        if not employee.user_id:
            continue

        sessions = frappe.get_all(
            "Voice Analysis Session",
            filters={
                "user": employee.user_id,
                "status": "Completed",
                "start_time": [">=", start_date]
            },
            fields=[
                "mode", "avg_stress_load", "avg_ps_score", "trigger_count"
            ]
        )

        individual = [s for s in sessions if s.mode == "Individual"]
        meetings = [s for s in sessions if s.mode == "Meeting"]

        member_data = {
            "employee": employee.name,
            "employee_name": employee.employee_name,
            "designation": employee.designation,
            "total_sessions": len(sessions),
            "individual_sessions": len(individual),
            "meeting_sessions": len(meetings)
        }

        if individual:
            stress_values = [s.avg_stress_load for s in individual if s.avg_stress_load]
            if stress_values:
                member_data["avg_stress"] = round(sum(stress_values) / len(stress_values), 3)

        if meetings:
            ps_values = [s.avg_ps_score for s in meetings if s.avg_ps_score]
            if ps_values:
                member_data["avg_ps"] = round(sum(ps_values) / len(ps_values), 3)

        team_data.append(member_data)

    # Sort by stress level (descending) to highlight those who may need support
    team_data.sort(key=lambda x: x.get("avg_stress", 0), reverse=True)

    return {
        "manager": manager,
        "period_days": 30,
        "team_size": len(reports),
        "active_members": len([m for m in team_data if m["total_sessions"] > 0]),
        "members": team_data
    }


@frappe.whitelist()
def get_organization_team_analysis(period: str = "month", department: str = None):
    """
    Get organization-wide team analysis (all employees with voice analysis data)

    Args:
        period: Time period (week, month, quarter)
        department: Optional department filter

    Returns:
        dict: Organization team analysis with individual metrics
    """
    roles = frappe.get_roles()
    if "Mind Analyzer Manager" not in roles and "Mind Analyzer Admin" not in roles and "System Manager" not in roles:
        frappe.throw(_("You don't have permission to view organization reports"))

    # Calculate date range
    today = getdate()
    if period == "week":
        start_date = add_days(today, -7)
        period_days = 7
    elif period == "quarter":
        start_date = add_days(today, -90)
        period_days = 90
    else:  # month
        start_date = add_days(today, -30)
        period_days = 30

    # Build employee filters
    emp_filters = {"status": "Active"}
    if department:
        emp_filters["department"] = department

    # Get all active employees
    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "user_id", "employee_name", "designation", "department"]
    )

    # Get users with voice analysis data
    users_with_data = frappe.db.sql("""
        SELECT DISTINCT user
        FROM `tabVoice Analysis Session`
        WHERE status = 'Completed'
        AND start_time >= %s
    """, (start_date,), as_dict=True)
    users_with_data = set(u.user for u in users_with_data)

    team_data = []

    for employee in employees:
        if not employee.user_id:
            continue

        # Skip if no data for this user
        if employee.user_id not in users_with_data:
            continue

        sessions = frappe.get_all(
            "Voice Analysis Session",
            filters={
                "user": employee.user_id,
                "status": "Completed",
                "start_time": [">=", start_date]
            },
            fields=[
                "mode", "avg_stress_load", "avg_ps_score", "trigger_count"
            ]
        )

        if not sessions:
            continue

        individual = [s for s in sessions if s.mode == "Individual"]
        meetings = [s for s in sessions if s.mode == "Meeting"]

        member_data = {
            "employee": employee.name,
            "employee_name": employee.employee_name,
            "designation": employee.designation,
            "department": employee.department,
            "user_id": employee.user_id,
            "total_sessions": len(sessions),
            "individual_sessions": len(individual),
            "meeting_sessions": len(meetings),
            "total_triggers": sum(s.trigger_count or 0 for s in sessions)
        }

        # Calculate individual session metrics
        if individual:
            stress_values = [s.avg_stress_load for s in individual if s.avg_stress_load is not None]
            if stress_values:
                member_data["avg_stress"] = round(sum(stress_values) / len(stress_values), 3)

        # Calculate meeting session metrics (PS score)
        if meetings:
            ps_values = [s.avg_ps_score for s in meetings if s.avg_ps_score is not None]
            if ps_values:
                member_data["avg_ps"] = round(sum(ps_values) / len(ps_values), 3)

        team_data.append(member_data)

    # Sort by stress level (descending) to highlight those who may need support
    team_data.sort(key=lambda x: x.get("avg_stress", 0), reverse=True)

    # Calculate organization averages
    all_stress = [m["avg_stress"] for m in team_data if "avg_stress" in m]
    all_ps = [m["avg_ps"] for m in team_data if "avg_ps" in m]

    return {
        "period": period,
        "period_days": period_days,
        "department": department,
        "team_size": len(employees),
        "active_members": len(team_data),
        "avg_stress": round(sum(all_stress) / len(all_stress), 3) if all_stress else None,
        "avg_ps": round(sum(all_ps) / len(all_ps), 3) if all_ps else None,
        "members": team_data
    }
