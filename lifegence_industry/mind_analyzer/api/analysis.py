# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import base64
import frappe
from frappe import _
from frappe.utils import now_datetime

from lifegence_mind_analyzer.api.session import has_analyzer_access


@frappe.whitelist()
def analyze_audio(session_id: str, audio_data: str, format: str = "webm"):
    """
    Analyze audio data and return results

    Args:
        session_id: Active session UUID
        audio_data: Base64 encoded audio data
        format: Audio format (webm, wav, pcm16)

    Returns:
        dict: Analysis results
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    # Find session
    session = frappe.db.get_value(
        "Voice Analysis Session",
        {"session_id": session_id, "status": "Active"},
        ["name", "mode", "user"],
        as_dict=True
    )

    if not session:
        frappe.throw(_("No active session found with this ID"))

    # Check ownership
    if session.user != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("You don't have permission to analyze in this session"))

    # Decode audio
    try:
        audio_bytes = base64.b64decode(audio_data)
    except Exception as e:
        frappe.throw(_("Invalid audio data: {0}").format(str(e)))

    # Import analysis services
    from lifegence_mind_analyzer.services.audio_processor import AudioProcessor
    from lifegence_mind_analyzer.services.trigger_detector import TriggerDetector

    # Process audio
    processor = AudioProcessor()
    stats = processor.process_audio(audio_bytes, format)

    # Save statistics
    from lifegence_mind_analyzer.mind_analyzer.doctype.acoustic_statistics.acoustic_statistics import AcousticStatistics
    AcousticStatistics.create_from_stats(session.name, stats)

    # Detect triggers
    detector = TriggerDetector()
    triggers = detector.detect(stats, session.name)

    # Save triggers
    from lifegence_mind_analyzer.mind_analyzer.doctype.voice_trigger_event.voice_trigger_event import VoiceTriggerEvent
    for trigger in triggers:
        VoiceTriggerEvent.create_trigger(session.name, trigger)

    # Run analysis based on mode
    if session.mode == "Individual":
        from lifegence_mind_analyzer.services.individual_analyzer import IndividualAnalyzer
        analyzer = IndividualAnalyzer()
        result = analyzer.analyze(stats, triggers)

        # Save result
        from lifegence_mind_analyzer.mind_analyzer.doctype.individual_analysis_result.individual_analysis_result import IndividualAnalysisResult
        result_doc = IndividualAnalysisResult.create_from_analysis(session.name, result)

        # Publish realtime update
        frappe.publish_realtime(
            "mind_analyzer_update",
            {
                "type": "individual_analysis",
                "session_id": session_id,
                "result": result
            },
            user=session.user
        )

        return {
            "success": True,
            "type": "individual",
            "result": result,
            "statistics": stats,
            "triggers": triggers
        }

    else:  # Meeting mode
        from lifegence_mind_analyzer.services.meeting_analyzer import MeetingAnalyzer
        analyzer = MeetingAnalyzer()
        result = analyzer.analyze(stats, triggers)

        # Save result
        from lifegence_mind_analyzer.mind_analyzer.doctype.meeting_analysis_result.meeting_analysis_result import MeetingAnalysisResult
        result_doc = MeetingAnalysisResult.create_from_analysis(session.name, result)

        # Publish realtime update
        frappe.publish_realtime(
            "mind_analyzer_update",
            {
                "type": "meeting_analysis",
                "session_id": session_id,
                "result": result
            },
            user=session.user
        )

        return {
            "success": True,
            "type": "meeting",
            "result": result,
            "statistics": stats,
            "triggers": triggers
        }


@frappe.whitelist()
def get_session_results(session_id: str = None, name: str = None):
    """
    Get all results for a session

    Args:
        session_id: UUID session identifier
        name: Frappe document name (alternative)

    Returns:
        dict: Session results including analysis and triggers
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    # Find session
    if session_id:
        session = frappe.db.get_value(
            "Voice Analysis Session",
            {"session_id": session_id},
            ["name", "mode", "user", "status", "start_time", "end_time",
             "duration_seconds", "avg_stress_load", "avg_ps_score"],
            as_dict=True
        )
    else:
        session = frappe.db.get_value(
            "Voice Analysis Session",
            {"name": name},
            ["name", "mode", "user", "status", "start_time", "end_time",
             "duration_seconds", "avg_stress_load", "avg_ps_score"],
            as_dict=True
        )

    if not session:
        frappe.throw(_("Session not found"))

    # Check permission
    if session.user != frappe.session.user:
        roles = frappe.get_roles()
        if "Mind Analyzer Manager" not in roles and "System Manager" not in roles:
            frappe.throw(_("You don't have permission to view this session"))

    # Get analysis results
    if session.mode == "Individual":
        results = frappe.get_all(
            "Individual Analysis Result",
            filters={"session": session.name},
            fields=["*"],
            order_by="timestamp asc"
        )
    else:
        results = frappe.get_all(
            "Meeting Analysis Result",
            filters={"session": session.name},
            fields=["*"],
            order_by="timestamp asc"
        )

    # Get triggers
    triggers = frappe.get_all(
        "Voice Trigger Event",
        filters={"session": session.name},
        fields=["trigger_type", "timestamp", "severity", "evidence"],
        order_by="timestamp asc"
    )

    # Get statistics
    statistics = frappe.get_all(
        "Acoustic Statistics",
        filters={"session": session.name},
        fields=["*"],
        order_by="timestamp asc"
    )

    return {
        "session": session,
        "results": results,
        "triggers": triggers,
        "statistics": statistics
    }


@frappe.whitelist()
def get_trend_data(employee: str = None, days: int = 30):
    """
    Get trend data for analysis over time

    Args:
        employee: Employee ID (optional, for managers)
        days: Number of days to look back

    Returns:
        dict: Trend data with daily averages
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    from frappe.utils import add_days, getdate

    # Determine user filter
    if employee:
        roles = frappe.get_roles()
        if "Mind Analyzer Manager" not in roles and "System Manager" not in roles:
            frappe.throw(_("You don't have permission to view other users' data"))
        user = frappe.db.get_value("Employee", employee, "user_id")
    else:
        user = frappe.session.user

    start_date = add_days(getdate(), -days)

    # Get sessions in date range
    sessions = frappe.get_all(
        "Voice Analysis Session",
        filters={
            "user": user,
            "status": "Completed",
            "start_time": [">=", start_date]
        },
        fields=["name", "mode", "start_time", "avg_stress_load", "avg_ps_score"],
        order_by="start_time asc"
    )

    # Calculate daily averages
    daily_data = {}
    for session in sessions:
        day = str(getdate(session.start_time))
        if day not in daily_data:
            daily_data[day] = {
                "individual_sessions": 0,
                "meeting_sessions": 0,
                "total_stress": 0,
                "total_ps": 0
            }

        if session.mode == "Individual":
            daily_data[day]["individual_sessions"] += 1
            if session.avg_stress_load:
                daily_data[day]["total_stress"] += session.avg_stress_load
        else:
            daily_data[day]["meeting_sessions"] += 1
            if session.avg_ps_score:
                daily_data[day]["total_ps"] += session.avg_ps_score

    # Calculate averages
    trend = []
    for day, data in daily_data.items():
        entry = {
            "date": day,
            "individual_sessions": data["individual_sessions"],
            "meeting_sessions": data["meeting_sessions"]
        }
        if data["individual_sessions"] > 0:
            entry["avg_stress"] = round(
                data["total_stress"] / data["individual_sessions"], 3
            )
        if data["meeting_sessions"] > 0:
            entry["avg_ps"] = round(
                data["total_ps"] / data["meeting_sessions"], 3
            )
        trend.append(entry)

    return {
        "user": user,
        "days": days,
        "trend": trend,
        "total_sessions": len(sessions)
    }


@frappe.whitelist()
def get_latest_result(session_id: str):
    """
    Get the latest analysis result for an active session

    Args:
        session_id: Active session UUID

    Returns:
        dict: Latest analysis result
    """
    if not has_analyzer_access():
        frappe.throw(_("You don't have permission to use Mind Analyzer"))

    session = frappe.db.get_value(
        "Voice Analysis Session",
        {"session_id": session_id},
        ["name", "mode", "user"],
        as_dict=True
    )

    if not session:
        frappe.throw(_("Session not found"))

    if session.user != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("You don't have permission to view this session"))

    # Get latest result based on mode
    if session.mode == "Individual":
        result = frappe.get_all(
            "Individual Analysis Result",
            filters={"session": session.name},
            fields=["*"],
            order_by="timestamp desc",
            limit=1
        )
    else:
        result = frappe.get_all(
            "Meeting Analysis Result",
            filters={"session": session.name},
            fields=["*"],
            order_by="timestamp desc",
            limit=1
        )

    # Get latest statistics
    stats = frappe.get_all(
        "Acoustic Statistics",
        filters={"session": session.name},
        fields=["*"],
        order_by="timestamp desc",
        limit=1
    )

    # Get recent triggers
    triggers = frappe.get_all(
        "Voice Trigger Event",
        filters={"session": session.name},
        fields=["trigger_type", "timestamp", "severity", "evidence"],
        order_by="timestamp desc",
        limit=5
    )

    return {
        "result": result[0] if result else None,
        "statistics": stats[0] if stats else None,
        "recent_triggers": triggers
    }
