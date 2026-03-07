# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist(allow_guest=True)
def has_analyzer_access():
    """Check if current user has access to mind analyzer"""
    try:
        user = frappe.session.user
        if not user or user == "Guest":
            return False

        if user == "Administrator":
            return True

        roles = frappe.get_roles(user)
        return any(role in roles for role in [
            "Mind Analyzer User",
            "Mind Analyzer Manager",
            "Mind Analyzer Admin",
            "System Manager"
        ])
    except Exception:
        return False


@frappe.whitelist()
def start_session(mode: str, meeting_title: str = None):
    """
    Start a new voice analysis session

    Args:
        mode: "Individual" or "Meeting"
        meeting_title: Title for meeting sessions (optional)

    Returns:
        dict: Session info including session_id
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    # Check for existing active session
    existing = frappe.db.get_value(
        "Voice Analysis Session",
        {"user": frappe.session.user, "status": "Active"},
        "name"
    )
    if existing:
        frappe.throw(_("You already have an active session. Please end it first."))

    # Validate mode
    if mode not in ["Individual", "Meeting"]:
        frappe.throw(_("Invalid mode. Must be 'Individual' or 'Meeting'"))

    # Create session
    session = frappe.new_doc("Voice Analysis Session")
    session.mode = mode
    session.user = frappe.session.user
    session.start_time = now_datetime()
    session.status = "Active"

    if mode == "Meeting":
        session.meeting_title = meeting_title or _("Untitled Meeting")

    session.insert()
    frappe.db.commit()

    return {
        "success": True,
        "session_id": session.session_id,
        "name": session.name,
        "mode": session.mode,
        "start_time": str(session.start_time)
    }


@frappe.whitelist()
def end_session(session_id: str = None, name: str = None):
    """
    End an active voice analysis session

    Args:
        session_id: UUID session identifier
        name: Frappe document name (alternative)

    Returns:
        dict: Session summary
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    # Find session
    if session_id:
        session_name = frappe.db.get_value(
            "Voice Analysis Session",
            {"session_id": session_id, "user": frappe.session.user},
            "name"
        )
    elif name:
        session_name = name
    else:
        # Get active session for current user
        session_name = frappe.db.get_value(
            "Voice Analysis Session",
            {"user": frappe.session.user, "status": "Active"},
            "name"
        )

    if not session_name:
        frappe.throw(_("No active session found"))

    session = frappe.get_doc("Voice Analysis Session", session_name)

    # Check ownership
    if session.user != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("You don't have permission to end this session"))

    # End session
    session.status = "Completed"
    session.end_time = now_datetime()
    session.save()
    frappe.db.commit()

    return {
        "success": True,
        "name": session.name,
        "session_id": session.session_id,
        "duration_seconds": session.duration_seconds,
        "trigger_count": session.trigger_count,
        "analysis_count": session.analysis_count,
        "avg_stress_load": session.avg_stress_load,
        "avg_ps_score": session.avg_ps_score
    }


@frappe.whitelist()
def get_active_session():
    """
    Get the current user's active session

    Returns:
        dict: Active session info or None
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    session = frappe.db.get_value(
        "Voice Analysis Session",
        {"user": frappe.session.user, "status": "Active"},
        ["name", "session_id", "mode", "start_time", "meeting_title"],
        as_dict=True
    )

    if not session:
        return {"active": False}

    return {
        "active": True,
        "name": session.name,
        "session_id": session.session_id,
        "mode": session.mode,
        "start_time": str(session.start_time),
        "meeting_title": session.meeting_title
    }


@frappe.whitelist()
def get_session_history(limit: int = 20, offset: int = 0, mode: str = None, days: int = None):
    """
    Get user's session history

    Args:
        limit: Number of sessions to return
        offset: Pagination offset
        mode: Filter by mode (Individual/Meeting)
        days: Filter by recent days

    Returns:
        list: List of session summaries
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    from frappe.utils import add_days, getdate

    filters = {"user": frappe.session.user, "status": "Completed"}

    if mode:
        filters["mode"] = mode

    if days:
        start_date = add_days(getdate(), -int(days))
        filters["start_time"] = [">=", start_date]

    sessions = frappe.get_all(
        "Voice Analysis Session",
        filters=filters,
        fields=[
            "name", "session_id", "mode", "status", "source",
            "start_time", "end_time", "duration_seconds",
            "avg_stress_load", "avg_ps_score", "trigger_count",
            "meeting_title"
        ],
        order_by="start_time desc",
        limit_page_length=limit,
        limit_start=offset
    )

    total = frappe.db.count("Voice Analysis Session", filters)

    return {
        "sessions": sessions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@frappe.whitelist()
def get_session_detail(session_name: str):
    """
    Get detailed information for a specific session

    Args:
        session_name: Session document name

    Returns:
        dict: Session details with metrics and triggers
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    session = frappe.get_doc("Voice Analysis Session", session_name)

    # Check ownership
    if session.user != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("You don't have permission to view this session"))

    # Get analysis results
    if session.mode == "Individual":
        results = frappe.get_all(
            "Individual Analysis Result",
            filters={"session": session_name},
            fields=[
                "timestamp", "stress_load", "anxiety_uncertainty",
                "cognitive_load", "confidence_assertiveness", "stability",
                "suggestion"
            ],
            order_by="timestamp desc"
        )

        # Calculate averages
        if results:
            avg_stress_load = sum(r.stress_load or 0 for r in results) / len(results)
            avg_anxiety = sum(r.anxiety_uncertainty or 0 for r in results) / len(results)
            avg_cognitive_load = sum(r.cognitive_load or 0 for r in results) / len(results)
            avg_confidence = sum(r.confidence_assertiveness or 0 for r in results) / len(results)
            avg_stability = sum(r.stability or 0 for r in results) / len(results)
        else:
            avg_stress_load = avg_anxiety = avg_cognitive_load = avg_confidence = avg_stability = None

        detail = {
            "avg_stress_load": round(avg_stress_load, 3) if avg_stress_load else None,
            "avg_anxiety": round(avg_anxiety, 3) if avg_anxiety else None,
            "avg_cognitive_load": round(avg_cognitive_load, 3) if avg_cognitive_load else None,
            "avg_confidence": round(avg_confidence, 3) if avg_confidence else None,
            "avg_stability": round(avg_stability, 3) if avg_stability else None,
            "results": results
        }
    else:
        results = frappe.get_all(
            "Meeting Analysis Result",
            filters={"session": session_name},
            fields=[
                "timestamp", "speak_up", "respect_interaction",
                "error_tolerance", "power_balance", "overall_ps"
            ],
            order_by="timestamp desc"
        )

        # Calculate averages
        if results:
            avg_speak_up = sum(r.speak_up or 0 for r in results) / len(results)
            avg_respect = sum(r.respect_interaction or 0 for r in results) / len(results)
            avg_error_tolerance = sum(r.error_tolerance or 0 for r in results) / len(results)
            avg_power_balance = sum(r.power_balance or 0 for r in results) / len(results)
            avg_ps_score = sum(r.overall_ps or 0 for r in results) / len(results)
        else:
            avg_speak_up = avg_respect = avg_error_tolerance = avg_power_balance = avg_ps_score = None

        detail = {
            "avg_speak_up": round(avg_speak_up, 3) if avg_speak_up else None,
            "avg_respect": round(avg_respect, 3) if avg_respect else None,
            "avg_error_tolerance": round(avg_error_tolerance, 3) if avg_error_tolerance else None,
            "avg_power_balance": round(avg_power_balance, 3) if avg_power_balance else None,
            "avg_ps_score": round(avg_ps_score, 3) if avg_ps_score else None,
            "results": results
        }

    # Get triggers
    triggers = frappe.get_all(
        "Voice Trigger Event",
        filters={"session": session_name},
        fields=["trigger_type", "severity", "evidence", "timestamp"],
        order_by="timestamp desc"
    )

    return {
        "name": session.name,
        "session_id": session.session_id,
        "mode": session.mode,
        "status": session.status,
        "source": session.source,
        "start_time": str(session.start_time),
        "end_time": str(session.end_time) if session.end_time else None,
        "duration_seconds": session.duration_seconds,
        "meeting_title": session.meeting_title,
        "triggers": triggers,
        **detail
    }


@frappe.whitelist()
def cancel_session(session_id: str = None, name: str = None):
    """
    Cancel an active session without saving results

    Args:
        session_id: UUID session identifier
        name: Frappe document name (alternative)

    Returns:
        dict: Cancellation confirmation
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    # Find session
    if session_id:
        session_name = frappe.db.get_value(
            "Voice Analysis Session",
            {"session_id": session_id, "user": frappe.session.user},
            "name"
        )
    elif name:
        session_name = name
    else:
        session_name = frappe.db.get_value(
            "Voice Analysis Session",
            {"user": frappe.session.user, "status": "Active"},
            "name"
        )

    if not session_name:
        frappe.throw(_("No active session found"))

    session = frappe.get_doc("Voice Analysis Session", session_name)

    if session.user != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("You don't have permission to cancel this session"))

    session.status = "Cancelled"
    session.end_time = now_datetime()
    session.save()
    frappe.db.commit()

    return {
        "success": True,
        "name": session.name,
        "session_id": session.session_id
    }
