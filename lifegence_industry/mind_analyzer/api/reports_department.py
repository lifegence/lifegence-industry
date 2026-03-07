# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Department-level analysis: summary, time series, and cross-department comparison.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate


@frappe.whitelist()
def get_department_summary(department: str, period: str = "month"):
    """
    Get department-level analysis summary

    Args:
        department: Department name
        period: Time period (week, month, quarter)

    Returns:
        dict: Department summary with aggregated metrics
    """
    # Check permission
    roles = frappe.get_roles()
    if "Mind Analyzer Manager" not in roles and "System Manager" not in roles:
        frappe.throw(_("You don't have permission to view department reports"))

    # Calculate date range
    today = getdate()
    if period == "week":
        start_date = add_days(today, -7)
    elif period == "quarter":
        start_date = add_days(today, -90)
    else:  # month
        start_date = add_days(today, -30)

    # Get employees in department
    employees = frappe.get_all(
        "Employee",
        filters={"department": department, "status": "Active"},
        fields=["name", "user_id", "employee_name"]
    )

    if not employees:
        return {
            "department": department,
            "period": period,
            "employee_count": 0,
            "sessions": []
        }

    user_ids = [e.user_id for e in employees if e.user_id]

    # Get sessions for department employees
    sessions = frappe.get_all(
        "Voice Analysis Session",
        filters={
            "user": ["in", user_ids],
            "status": "Completed",
            "start_time": [">=", start_date]
        },
        fields=[
            "name", "mode", "user", "start_time",
            "avg_stress_load", "avg_ps_score", "trigger_count"
        ]
    )

    # Calculate department metrics
    individual_sessions = [s for s in sessions if s.mode == "Individual"]
    meeting_sessions = [s for s in sessions if s.mode == "Meeting"]

    avg_stress = 0
    if individual_sessions:
        stress_values = [s.avg_stress_load for s in individual_sessions if s.avg_stress_load]
        if stress_values:
            avg_stress = sum(stress_values) / len(stress_values)

    avg_ps = 0
    if meeting_sessions:
        ps_values = [s.avg_ps_score for s in meeting_sessions if s.avg_ps_score]
        if ps_values:
            avg_ps = sum(ps_values) / len(ps_values)

    total_triggers = sum(s.trigger_count or 0 for s in sessions)

    # Get active users
    active_users = len(set(s.user for s in sessions))

    return {
        "department": department,
        "period": period,
        "start_date": str(start_date),
        "end_date": str(today),
        "employee_count": len(employees),
        "active_users": active_users,
        "total_sessions": len(sessions),
        "individual_sessions": len(individual_sessions),
        "meeting_sessions": len(meeting_sessions),
        "avg_stress_load": round(avg_stress, 3),
        "avg_ps_score": round(avg_ps, 3),
        "total_triggers": total_triggers,
        "participation_rate": round(active_users / len(employees) * 100, 1) if employees else 0
    }


@frappe.whitelist()
def get_department_timeseries(period: str = "month"):
    """
    Get time series data for stress/PS scores by department

    Args:
        period: Time period (week, month, quarter)

    Returns:
        dict: Time series data by department
    """
    roles = frappe.get_roles()
    if "Mind Analyzer Manager" not in roles and "Mind Analyzer Admin" not in roles and "System Manager" not in roles:
        frappe.throw(_("You don't have permission to view organization reports"))

    today = getdate()
    if period == "week":
        start_date = add_days(today, -7)
        interval = "day"
    elif period == "quarter":
        start_date = add_days(today, -90)
        interval = "week"
    else:  # month
        start_date = add_days(today, -30)
        interval = "day"

    # Get all departments
    departments = frappe.get_all(
        "Department",
        filters={"is_group": 0},
        fields=["name"]
    )

    # Get date format based on interval
    if interval == "week":
        date_sql = "DATE_FORMAT(vas.start_time, '%Y-W%u')"
    else:
        date_sql = "DATE(vas.start_time)"

    result = {
        "period": period,
        "interval": interval,
        "departments": [],
        "dates": [],
        "series": {}
    }

    # Get all dates in range first
    all_dates = set()

    for dept in departments:
        dept_name = dept.name

        # Get employees in this department
        employees = frappe.get_all(
            "Employee",
            filters={"department": dept_name, "status": "Active"},
            fields=["user_id"]
        )
        user_ids = [e.user_id for e in employees if e.user_id]

        if not user_ids:
            continue

        # Get session data grouped by date
        data = frappe.db.sql(f"""
            SELECT
                {date_sql} as date_group,
                AVG(vas.avg_stress_load) as avg_stress,
                AVG(vas.avg_ps_score) as avg_ps,
                COUNT(*) as session_count
            FROM `tabVoice Analysis Session` vas
            WHERE vas.user IN ({','.join(['%s'] * len(user_ids))})
            AND vas.status = 'Completed'
            AND vas.start_time >= %s
            GROUP BY date_group
            ORDER BY date_group
        """, user_ids + [start_date], as_dict=True)

        if not data:
            continue

        result["departments"].append(dept_name)
        result["series"][dept_name] = {
            "stress": {},
            "ps": {},
            "sessions": {}
        }

        for row in data:
            date_key = str(row.date_group)
            all_dates.add(date_key)
            result["series"][dept_name]["stress"][date_key] = round(row.avg_stress * 100, 1) if row.avg_stress else None
            result["series"][dept_name]["ps"][date_key] = round(row.avg_ps * 100, 1) if row.avg_ps else None
            result["series"][dept_name]["sessions"][date_key] = row.session_count

    # Sort dates
    result["dates"] = sorted(list(all_dates))

    return result


@frappe.whitelist()
def get_department_comparison():
    """
    Get comparison data across all departments

    Returns:
        dict: Department comparison metrics
    """
    roles = frappe.get_roles()
    if "Mind Analyzer Manager" not in roles and "Mind Analyzer Admin" not in roles and "System Manager" not in roles:
        frappe.throw(_("You don't have permission to view organization reports"))

    today = getdate()
    start_date = add_days(today, -30)

    departments = frappe.get_all(
        "Department",
        filters={"is_group": 0},
        fields=["name"]
    )

    result = []

    for dept in departments:
        dept_name = dept.name

        employees = frappe.get_all(
            "Employee",
            filters={"department": dept_name, "status": "Active"},
            fields=["user_id"]
        )
        user_ids = [e.user_id for e in employees if e.user_id]

        if not user_ids:
            continue

        # Get aggregate metrics
        data = frappe.db.sql("""
            SELECT
                AVG(avg_stress_load) as avg_stress,
                AVG(avg_ps_score) as avg_ps,
                COUNT(*) as total_sessions,
                SUM(trigger_count) as total_triggers
            FROM `tabVoice Analysis Session`
            WHERE user IN ({})
            AND status = 'Completed'
            AND start_time >= %s
        """.format(','.join(['%s'] * len(user_ids))), user_ids + [start_date], as_dict=True)

        if data and data[0].total_sessions:
            row = data[0]
            result.append({
                "department": dept_name,
                "avg_stress": round(row.avg_stress * 100, 1) if row.avg_stress else None,
                "avg_ps": round(row.avg_ps * 100, 1) if row.avg_ps else None,
                "total_sessions": row.total_sessions,
                "total_triggers": row.total_triggers or 0,
                "employee_count": len(user_ids)
            })

    # Sort by stress (highest first)
    result.sort(key=lambda x: x.get("avg_stress") or 0, reverse=True)

    return {
        "departments": result,
        "period_days": 30
    }
