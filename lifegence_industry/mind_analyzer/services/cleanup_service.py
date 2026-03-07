# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Cleanup Service
Handles data retention and cleanup tasks
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, getdate


def cleanup_old_data():
    """
    Scheduled task: Clean up old analysis data based on retention policy

    Called daily via scheduler_events in hooks.py
    """
    try:
        settings = frappe.get_single("Voice Analyzer Settings")
        retention_days = settings.data_retention_days or 90
    except Exception:
        retention_days = 90

    cutoff_date = add_days(getdate(), -retention_days)

    # Get old sessions
    old_sessions = frappe.get_all(
        "Voice Analysis Session",
        filters={
            "start_time": ["<", cutoff_date],
            "status": ["in", ["Completed", "Cancelled"]]
        },
        fields=["name"]
    )

    deleted_count = 0
    for session in old_sessions:
        try:
            _delete_session_data(session.name)
            deleted_count += 1
        except Exception as e:
            frappe.log_error(
                f"Failed to delete session {session.name}: {str(e)}",
                "Mind Analyzer Cleanup"
            )

    if deleted_count > 0:
        frappe.logger().info(
            f"Mind Analyzer: Cleaned up {deleted_count} sessions older than {retention_days} days"
        )


def cleanup_stale_sessions():
    """
    Scheduled task: Clean up stale active sessions

    Sessions that have been "Active" for more than 24 hours are likely abandoned.
    Called every 6 hours via scheduler_events in hooks.py
    """
    cutoff_time = add_days(now_datetime(), -1)  # 24 hours ago

    stale_sessions = frappe.get_all(
        "Voice Analysis Session",
        filters={
            "status": "Active",
            "start_time": ["<", cutoff_time]
        },
        fields=["name", "user", "start_time"]
    )

    for session in stale_sessions:
        try:
            doc = frappe.get_doc("Voice Analysis Session", session.name)
            doc.status = "Cancelled"
            doc.end_time = now_datetime()
            doc.save(ignore_permissions=True)

            frappe.logger().info(
                f"Mind Analyzer: Cancelled stale session {session.name} "
                f"(started: {session.start_time}, user: {session.user})"
            )
        except Exception as e:
            frappe.log_error(
                f"Failed to cancel stale session {session.name}: {str(e)}",
                "Mind Analyzer Cleanup"
            )

    frappe.db.commit()


def _delete_session_data(session_name: str):
    """
    Delete all data associated with a session

    Args:
        session_name: Session document name
    """
    # Delete child records first
    child_doctypes = [
        "Individual Analysis Result",
        "Meeting Analysis Result",
        "Voice Trigger Event",
        "Acoustic Statistics"
    ]

    for doctype in child_doctypes:
        frappe.db.delete(doctype, {"session": session_name})

    # Delete the session itself
    frappe.delete_doc("Voice Analysis Session", session_name, force=True)
    frappe.db.commit()


def get_data_statistics():
    """
    Get statistics about stored data

    Returns:
        dict: Data statistics
    """
    stats = {
        "total_sessions": frappe.db.count("Voice Analysis Session"),
        "active_sessions": frappe.db.count("Voice Analysis Session", {"status": "Active"}),
        "completed_sessions": frappe.db.count("Voice Analysis Session", {"status": "Completed"}),
        "individual_results": frappe.db.count("Individual Analysis Result"),
        "meeting_results": frappe.db.count("Meeting Analysis Result"),
        "trigger_events": frappe.db.count("Voice Trigger Event"),
        "acoustic_stats": frappe.db.count("Acoustic Statistics"),
    }

    # Calculate storage estimate (rough)
    # Assuming average record size of 2KB
    total_records = sum([
        stats["individual_results"],
        stats["meeting_results"],
        stats["trigger_events"],
        stats["acoustic_stats"]
    ])
    stats["estimated_storage_mb"] = round(total_records * 2 / 1024, 2)

    return stats


def manual_cleanup(days: int = None, dry_run: bool = True):
    """
    Manual cleanup function for administrative use

    Args:
        days: Delete data older than this many days (overrides settings)
        dry_run: If True, only report what would be deleted

    Returns:
        dict: Cleanup report
    """
    if not frappe.has_permission("Voice Analyzer Settings", "write"):
        frappe.throw(_("You don't have permission to perform cleanup"))

    if days is None:
        try:
            settings = frappe.get_single("Voice Analyzer Settings")
            days = settings.data_retention_days or 90
        except Exception:
            days = 90

    cutoff_date = add_days(getdate(), -days)

    # Count records to be deleted
    sessions = frappe.get_all(
        "Voice Analysis Session",
        filters={
            "start_time": ["<", cutoff_date],
            "status": ["in", ["Completed", "Cancelled"]]
        },
        fields=["name"]
    )

    session_names = [s.name for s in sessions]

    report = {
        "cutoff_date": str(cutoff_date),
        "sessions_to_delete": len(sessions),
        "dry_run": dry_run
    }

    if session_names:
        report["individual_results"] = frappe.db.count(
            "Individual Analysis Result",
            {"session": ["in", session_names]}
        )
        report["meeting_results"] = frappe.db.count(
            "Meeting Analysis Result",
            {"session": ["in", session_names]}
        )
        report["trigger_events"] = frappe.db.count(
            "Voice Trigger Event",
            {"session": ["in", session_names]}
        )
        report["acoustic_stats"] = frappe.db.count(
            "Acoustic Statistics",
            {"session": ["in", session_names]}
        )
    else:
        report["individual_results"] = 0
        report["meeting_results"] = 0
        report["trigger_events"] = 0
        report["acoustic_stats"] = 0

    if not dry_run and sessions:
        deleted = 0
        for session in sessions:
            try:
                _delete_session_data(session.name)
                deleted += 1
            except Exception as e:
                frappe.log_error(f"Manual cleanup failed for {session.name}: {str(e)}")

        report["deleted_sessions"] = deleted

    return report
