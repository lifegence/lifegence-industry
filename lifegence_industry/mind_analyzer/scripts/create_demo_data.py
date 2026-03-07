"""
Demo Data Generator for Lifegence Mind Analyzer
Creates realistic demo data for testing and demonstration purposes.

Usage:
    bench execute lifegence_industry.mind_analyzer.scripts.create_demo_data.create_all_demo_data

To clear demo data:
    bench execute lifegence_industry.mind_analyzer.scripts.create_demo_data.clear_demo_data
"""

import frappe
from frappe.utils import now_datetime, add_to_date, get_datetime
import random
import uuid
import json
from datetime import timedelta


def create_all_demo_data():
    """Main function to create all demo data."""
    frappe.flags.ignore_permissions = True

    print("🚀 Starting demo data creation for Lifegence Mind Analyzer...")

    # Create demo users if they don't exist
    create_demo_users()

    # Create demo sessions
    sessions = create_demo_sessions()

    print(f"✅ Created {len(sessions)} demo sessions with associated data")
    print("📊 Demo data creation completed!")

    frappe.db.commit()
    return sessions


def create_demo_users():
    """Create demo users for testing."""
    demo_users = [
        {"email": "demo.user@example.com", "first_name": "Demo", "last_name": "User"},
        {"email": "manager@example.com", "first_name": "Manager", "last_name": "Test"},
        {"email": "team.member@example.com", "first_name": "Team", "last_name": "Member"},
    ]

    for user_data in demo_users:
        if not frappe.db.exists("User", user_data["email"]):
            user = frappe.get_doc({
                "doctype": "User",
                "email": user_data["email"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "enabled": 1,
                "user_type": "System User",
                "send_welcome_email": 0,
            })
            user.insert(ignore_permissions=True)
            print(f"  👤 Created user: {user_data['email']}")
        else:
            print(f"  ℹ️ User already exists: {user_data['email']}")


def create_demo_sessions():
    """Create various demo sessions with different scenarios."""
    sessions = []

    # Scenario 1: Healthy individual session (low stress)
    sessions.append(create_individual_session_healthy())

    # Scenario 2: Stressed individual session (high stress)
    sessions.append(create_individual_session_stressed())

    # Scenario 3: Recovery individual session (stress decreasing over time)
    sessions.append(create_individual_session_recovery())

    # Scenario 4: Healthy meeting (high psychological safety)
    sessions.append(create_meeting_session_healthy())

    # Scenario 5: Problematic meeting (low psychological safety)
    sessions.append(create_meeting_session_problematic())

    # Scenario 6: Improving meeting (PS score improving over time)
    sessions.append(create_meeting_session_improving())

    return sessions


def create_individual_session_healthy():
    """Create a healthy individual analysis session."""
    print("\n📗 Creating healthy individual session...")

    base_time = add_to_date(now_datetime(), days=-1, hours=-2)
    duration = 1800  # 30 minutes

    session = frappe.get_doc({
        "doctype": "Voice Analysis Session",
        "session_id": str(uuid.uuid4()),
        "mode": "Individual",
        "status": "Completed",
        "source": "chat",
        "user": "demo.user@example.com",
        "start_time": base_time,
        "end_time": add_to_date(base_time, seconds=duration),
    })
    session.insert(ignore_permissions=True)

    # Create 6 analysis results (every 5 minutes)
    for i in range(6):
        timestamp = add_to_date(base_time, minutes=i*5)
        create_individual_analysis_result(
            session.name,
            timestamp,
            stress_load=random.uniform(0.15, 0.30),
            anxiety_uncertainty=random.uniform(0.10, 0.25),
            cognitive_load=random.uniform(0.25, 0.40),
            confidence_assertiveness=random.uniform(0.70, 0.85),
            stability=random.uniform(0.75, 0.90),
        )

    # Create acoustic statistics
    for i in range(6):
        timestamp = add_to_date(base_time, minutes=i*5)
        create_acoustic_statistics(
            session.name,
            timestamp,
            speech_ratio=random.uniform(0.55, 0.70),
            silence_mean_ms=random.uniform(400, 600),
            silence_max_ms=random.uniform(1000, 1500),
            speech_rate_relative=random.uniform(0.95, 1.05),
            filler_rate=random.uniform(0.01, 0.03),
        )

    # Few triggers (healthy state)
    create_voice_trigger_event(
        session.name,
        add_to_date(base_time, minutes=12),
        "hedge_increase",
        severity=0.25,
        evidence="軽度の言い淀みが検出されましたが、正常範囲内です"
    )

    session.reload()
    print(f"  ✅ Created session: {session.name}")
    return session


def create_individual_session_stressed():
    """Create a stressed individual analysis session."""
    print("\n📕 Creating stressed individual session...")

    base_time = add_to_date(now_datetime(), days=-2, hours=-4)
    duration = 2400  # 40 minutes

    session = frappe.get_doc({
        "doctype": "Voice Analysis Session",
        "session_id": str(uuid.uuid4()),
        "mode": "Individual",
        "status": "Completed",
        "source": "chat",
        "user": "team.member@example.com",
        "start_time": base_time,
        "end_time": add_to_date(base_time, seconds=duration),
    })
    session.insert(ignore_permissions=True)

    # Create 8 analysis results showing high stress
    for i in range(8):
        timestamp = add_to_date(base_time, minutes=i*5)
        create_individual_analysis_result(
            session.name,
            timestamp,
            stress_load=random.uniform(0.65, 0.85),
            anxiety_uncertainty=random.uniform(0.55, 0.75),
            cognitive_load=random.uniform(0.70, 0.85),
            confidence_assertiveness=random.uniform(0.25, 0.40),
            stability=random.uniform(0.20, 0.40),
        )

    # Create acoustic statistics showing stress indicators
    for i in range(8):
        timestamp = add_to_date(base_time, minutes=i*5)
        create_acoustic_statistics(
            session.name,
            timestamp,
            speech_ratio=random.uniform(0.35, 0.50),
            silence_mean_ms=random.uniform(800, 1200),
            silence_max_ms=random.uniform(3000, 5000),
            speech_rate_relative=random.uniform(1.20, 1.40),
            filler_rate=random.uniform(0.08, 0.15),
        )

    # Multiple triggers indicating stress
    triggers = [
        ("silence_spike", 0.72, "長時間の沈黙が検出されました（4.2秒）"),
        ("hedge_increase", 0.65, "「たぶん」「おそらく」などの曖昧表現が増加"),
        ("speech_rate_change", 0.58, "発話速度が基準値より35%上昇"),
        ("restart_increase", 0.61, "言い直しが1分間に6回検出"),
        ("apology_phrase", 0.55, "謝罪フレーズ「すみません」が頻出"),
    ]

    for i, (trigger_type, severity, evidence) in enumerate(triggers):
        create_voice_trigger_event(
            session.name,
            add_to_date(base_time, minutes=5 + i*7),
            trigger_type,
            severity=severity,
            evidence=evidence
        )

    session.reload()
    print(f"  ✅ Created session: {session.name}")
    return session


def create_individual_session_recovery():
    """Create an individual session showing stress recovery."""
    print("\n📙 Creating recovery individual session...")

    base_time = add_to_date(now_datetime(), hours=-6)
    duration = 3600  # 60 minutes

    session = frappe.get_doc({
        "doctype": "Voice Analysis Session",
        "session_id": str(uuid.uuid4()),
        "mode": "Individual",
        "status": "Completed",
        "source": "batch",
        "user": "demo.user@example.com",
        "start_time": base_time,
        "end_time": add_to_date(base_time, seconds=duration),
    })
    session.insert(ignore_permissions=True)

    # Create 12 analysis results showing gradual improvement
    for i in range(12):
        timestamp = add_to_date(base_time, minutes=i*5)
        progress = i / 11  # 0 to 1 over the session

        create_individual_analysis_result(
            session.name,
            timestamp,
            stress_load=0.75 - (0.50 * progress) + random.uniform(-0.05, 0.05),
            anxiety_uncertainty=0.65 - (0.45 * progress) + random.uniform(-0.05, 0.05),
            cognitive_load=0.70 - (0.35 * progress) + random.uniform(-0.05, 0.05),
            confidence_assertiveness=0.30 + (0.45 * progress) + random.uniform(-0.05, 0.05),
            stability=0.30 + (0.50 * progress) + random.uniform(-0.05, 0.05),
        )

    # Acoustic statistics also improving
    for i in range(12):
        timestamp = add_to_date(base_time, minutes=i*5)
        progress = i / 11

        create_acoustic_statistics(
            session.name,
            timestamp,
            speech_ratio=0.40 + (0.25 * progress),
            silence_mean_ms=1000 - (400 * progress),
            silence_max_ms=4000 - (2500 * progress),
            speech_rate_relative=1.30 - (0.25 * progress),
            filler_rate=0.12 - (0.08 * progress),
        )

    # Early triggers (stress), none in later half
    create_voice_trigger_event(
        session.name,
        add_to_date(base_time, minutes=5),
        "silence_spike",
        severity=0.65,
        evidence="セッション開始時に長い沈黙を検出"
    )
    create_voice_trigger_event(
        session.name,
        add_to_date(base_time, minutes=15),
        "speech_rate_change",
        severity=0.55,
        evidence="発話速度が不安定"
    )

    session.reload()
    print(f"  ✅ Created session: {session.name}")
    return session


def create_meeting_session_healthy():
    """Create a healthy meeting session with high psychological safety."""
    print("\n📘 Creating healthy meeting session...")

    base_time = add_to_date(now_datetime(), days=-1, hours=-5)
    duration = 3600  # 60 minutes

    session = frappe.get_doc({
        "doctype": "Voice Analysis Session",
        "session_id": str(uuid.uuid4()),
        "mode": "Meeting",
        "status": "Completed",
        "source": "chat",
        "user": "manager@example.com",
        "start_time": base_time,
        "end_time": add_to_date(base_time, seconds=duration),
        "meeting_title": "週次チームミーティング",
        "participants_count": 5,
    })
    session.insert(ignore_permissions=True)

    # Create 6 meeting analysis results
    for i in range(6):
        timestamp = add_to_date(base_time, minutes=i*10)
        create_meeting_analysis_result(
            session.name,
            timestamp,
            speak_up=random.uniform(0.78, 0.92),
            respect_interaction=random.uniform(0.80, 0.95),
            error_tolerance=random.uniform(0.75, 0.88),
            power_balance=random.uniform(0.72, 0.85),
            key_moments=[
                {"time": str(add_to_date(timestamp, minutes=2)), "event": "活発な議論", "impact": "positive"},
                {"time": str(add_to_date(timestamp, minutes=5)), "event": "建設的なフィードバック", "impact": "positive"},
            ],
            speaker_stats={
                "speaker_1": {"speaking_time_pct": 0.22, "interruptions": 0},
                "speaker_2": {"speaking_time_pct": 0.20, "interruptions": 1},
                "speaker_3": {"speaking_time_pct": 0.19, "interruptions": 0},
                "speaker_4": {"speaking_time_pct": 0.21, "interruptions": 1},
                "speaker_5": {"speaking_time_pct": 0.18, "interruptions": 0},
            }
        )

    # Create acoustic statistics
    for i in range(6):
        timestamp = add_to_date(base_time, minutes=i*10)
        create_acoustic_statistics(
            session.name,
            timestamp,
            speech_ratio=random.uniform(0.65, 0.80),
            silence_mean_ms=random.uniform(300, 500),
            silence_max_ms=random.uniform(800, 1200),
            speech_rate_relative=random.uniform(0.95, 1.05),
            filler_rate=random.uniform(0.02, 0.04),
        )

    # Minimal triggers
    create_voice_trigger_event(
        session.name,
        add_to_date(base_time, minutes=25),
        "overlap",
        severity=0.20,
        evidence="熱心な議論による軽微な発言の重なり"
    )

    session.reload()
    print(f"  ✅ Created session: {session.name}")
    return session


def create_meeting_session_problematic():
    """Create a problematic meeting session with low psychological safety."""
    print("\n📕 Creating problematic meeting session...")

    base_time = add_to_date(now_datetime(), days=-3, hours=-2)
    duration = 5400  # 90 minutes (dragging meeting)

    session = frappe.get_doc({
        "doctype": "Voice Analysis Session",
        "session_id": str(uuid.uuid4()),
        "mode": "Meeting",
        "status": "Completed",
        "source": "chat",
        "user": "manager@example.com",
        "start_time": base_time,
        "end_time": add_to_date(base_time, seconds=duration),
        "meeting_title": "プロジェクト進捗報告会",
        "participants_count": 6,
    })
    session.insert(ignore_permissions=True)

    # Create 9 meeting analysis results showing problems
    for i in range(9):
        timestamp = add_to_date(base_time, minutes=i*10)
        create_meeting_analysis_result(
            session.name,
            timestamp,
            speak_up=random.uniform(0.25, 0.40),
            respect_interaction=random.uniform(0.30, 0.45),
            error_tolerance=random.uniform(0.20, 0.35),
            power_balance=random.uniform(0.18, 0.30),
            key_moments=[
                {"time": str(add_to_date(timestamp, minutes=3)), "event": "長い沈黙", "impact": "negative"},
                {"time": str(add_to_date(timestamp, minutes=7)), "event": "一方的な発言", "impact": "negative"},
            ],
            speaker_stats={
                "speaker_1": {"speaking_time_pct": 0.55, "interruptions": 8},  # Dominant speaker
                "speaker_2": {"speaking_time_pct": 0.15, "interruptions": 0},
                "speaker_3": {"speaking_time_pct": 0.12, "interruptions": 0},
                "speaker_4": {"speaking_time_pct": 0.08, "interruptions": 0},
                "speaker_5": {"speaking_time_pct": 0.06, "interruptions": 0},
                "speaker_6": {"speaking_time_pct": 0.04, "interruptions": 0},
            }
        )

    # Acoustic statistics showing disengagement
    for i in range(9):
        timestamp = add_to_date(base_time, minutes=i*10)
        create_acoustic_statistics(
            session.name,
            timestamp,
            speech_ratio=random.uniform(0.30, 0.45),
            silence_mean_ms=random.uniform(1200, 2000),
            silence_max_ms=random.uniform(5000, 8000),
            speech_rate_relative=random.uniform(0.80, 0.90),
            filler_rate=random.uniform(0.08, 0.15),
        )

    # Many triggers indicating problems
    triggers = [
        ("power_imbalance", 0.85, "発言時間の偏りが著しい（1名が55%を占有）"),
        ("silence_spike", 0.75, "質問後に6.5秒の沈黙"),
        ("interruption", 0.70, "speaker_1による頻繁な割り込み"),
        ("silence_spike", 0.72, "提案後に長い沈黙が続く"),
        ("hedge_increase", 0.65, "参加者全体で曖昧表現が増加"),
        ("apology_phrase", 0.60, "謝罪から始まる発言が多い"),
        ("interruption", 0.68, "建設的な意見が遮られる"),
    ]

    for i, (trigger_type, severity, evidence) in enumerate(triggers):
        create_voice_trigger_event(
            session.name,
            add_to_date(base_time, minutes=10 + i*12),
            trigger_type,
            severity=severity,
            evidence=evidence
        )

    session.reload()
    print(f"  ✅ Created session: {session.name}")
    return session


def create_meeting_session_improving():
    """Create a meeting session showing improvement over time."""
    print("\n📙 Creating improving meeting session...")

    base_time = add_to_date(now_datetime(), hours=-3)
    duration = 4500  # 75 minutes

    session = frappe.get_doc({
        "doctype": "Voice Analysis Session",
        "session_id": str(uuid.uuid4()),
        "mode": "Meeting",
        "status": "Completed",
        "source": "api",
        "user": "manager@example.com",
        "start_time": base_time,
        "end_time": add_to_date(base_time, seconds=duration),
        "meeting_title": "ブレインストーミングセッション",
        "participants_count": 4,
    })
    session.insert(ignore_permissions=True)

    # Create 7 meeting analysis results showing gradual improvement
    for i in range(7):
        timestamp = add_to_date(base_time, minutes=i*10)
        progress = i / 6  # 0 to 1 over the meeting

        create_meeting_analysis_result(
            session.name,
            timestamp,
            speak_up=0.35 + (0.50 * progress) + random.uniform(-0.05, 0.05),
            respect_interaction=0.40 + (0.45 * progress) + random.uniform(-0.05, 0.05),
            error_tolerance=0.35 + (0.45 * progress) + random.uniform(-0.05, 0.05),
            power_balance=0.30 + (0.50 * progress) + random.uniform(-0.05, 0.05),
            key_moments=[
                {"time": str(add_to_date(timestamp, minutes=3)),
                 "event": "徐々に発言が増加" if progress > 0.3 else "控えめな発言",
                 "impact": "positive" if progress > 0.3 else "neutral"},
            ],
            speaker_stats={
                "speaker_1": {"speaking_time_pct": 0.40 - (0.15 * progress), "interruptions": max(0, int(5 - 5*progress))},
                "speaker_2": {"speaking_time_pct": 0.20 + (0.05 * progress), "interruptions": 0},
                "speaker_3": {"speaking_time_pct": 0.20 + (0.05 * progress), "interruptions": 0},
                "speaker_4": {"speaking_time_pct": 0.20 + (0.05 * progress), "interruptions": 0},
            }
        )

    # Acoustic statistics improving
    for i in range(7):
        timestamp = add_to_date(base_time, minutes=i*10)
        progress = i / 6

        create_acoustic_statistics(
            session.name,
            timestamp,
            speech_ratio=0.40 + (0.30 * progress),
            silence_mean_ms=1500 - (1000 * progress),
            silence_max_ms=5000 - (3500 * progress),
            speech_rate_relative=0.85 + (0.15 * progress),
            filler_rate=0.10 - (0.06 * progress),
        )

    # Early triggers, none in later half
    create_voice_trigger_event(
        session.name,
        add_to_date(base_time, minutes=8),
        "silence_spike",
        severity=0.55,
        evidence="ミーティング開始時の緊張による沈黙"
    )
    create_voice_trigger_event(
        session.name,
        add_to_date(base_time, minutes=18),
        "power_imbalance",
        severity=0.48,
        evidence="初期は一部の参加者が主導"
    )

    session.reload()
    print(f"  ✅ Created session: {session.name}")
    return session


def create_individual_analysis_result(session_name, timestamp, **metrics):
    """Create an Individual Analysis Result."""
    # Clamp values to 0-1 range
    for key in metrics:
        metrics[key] = max(0.0, min(1.0, metrics[key]))

    evidence = generate_individual_evidence(metrics)
    suggestion = generate_individual_suggestion(metrics)

    doc = frappe.get_doc({
        "doctype": "Individual Analysis Result",
        "session": session_name,
        "timestamp": timestamp,
        "stress_load": metrics.get("stress_load", 0.5),
        "anxiety_uncertainty": metrics.get("anxiety_uncertainty", 0.5),
        "cognitive_load": metrics.get("cognitive_load", 0.5),
        "confidence_assertiveness": metrics.get("confidence_assertiveness", 0.5),
        "stability": metrics.get("stability", 0.5),
        "analysis_confidence": random.uniform(0.85, 0.95),
        "evidence": json.dumps(evidence, ensure_ascii=False),
        "suggestion": suggestion,
    })
    doc.insert(ignore_permissions=True)
    return doc


def create_meeting_analysis_result(session_name, timestamp, key_moments=None, speaker_stats=None, **metrics):
    """Create a Meeting Analysis Result."""
    # Clamp values to 0-1 range
    for key in metrics:
        if isinstance(metrics[key], (int, float)):
            metrics[key] = max(0.0, min(1.0, metrics[key]))

    # Calculate overall PS score
    overall_ps = (
        metrics.get("speak_up", 0.5) * 0.25 +
        metrics.get("respect_interaction", 0.5) * 0.25 +
        metrics.get("error_tolerance", 0.5) * 0.25 +
        metrics.get("power_balance", 0.5) * 0.25
    )

    doc = frappe.get_doc({
        "doctype": "Meeting Analysis Result",
        "session": session_name,
        "timestamp": timestamp,
        "speak_up": metrics.get("speak_up", 0.5),
        "respect_interaction": metrics.get("respect_interaction", 0.5),
        "error_tolerance": metrics.get("error_tolerance", 0.5),
        "power_balance": metrics.get("power_balance", 0.5),
        "overall_ps": overall_ps,
        "analysis_confidence": random.uniform(0.82, 0.94),
        "key_moments": json.dumps(key_moments or [], ensure_ascii=False),
        "speaker_stats": json.dumps(speaker_stats or {}, ensure_ascii=False),
    })
    doc.insert(ignore_permissions=True)
    return doc


def create_acoustic_statistics(session_name, timestamp, **stats):
    """Create Acoustic Statistics."""
    doc = frappe.get_doc({
        "doctype": "Acoustic Statistics",
        "session": session_name,
        "timestamp": timestamp,
        "speech_ratio": stats.get("speech_ratio", 0.5),
        "silence_mean_ms": stats.get("silence_mean_ms", 500),
        "silence_max_ms": stats.get("silence_max_ms", 1500),
        "speech_rate_relative": stats.get("speech_rate_relative", 1.0),
        "filler_rate": stats.get("filler_rate", 0.05),
        "rms_level": stats.get("rms_level", random.uniform(0.3, 0.7)),
        "rms_variance": stats.get("rms_variance", random.uniform(0.05, 0.15)),
    })
    doc.insert(ignore_permissions=True)
    return doc


def create_voice_trigger_event(session_name, timestamp, trigger_type, severity, evidence):
    """Create a Voice Trigger Event."""
    doc = frappe.get_doc({
        "doctype": "Voice Trigger Event",
        "session": session_name,
        "trigger_type": trigger_type,
        "timestamp": timestamp,
        "severity": max(0.0, min(1.0, severity)),
        "evidence": evidence,
        "metadata": json.dumps({
            "auto_generated": True,
            "demo_data": True,
        }, ensure_ascii=False),
    })
    doc.insert(ignore_permissions=True)
    return doc


def generate_individual_evidence(metrics):
    """Generate evidence list based on metrics."""
    evidence = []

    if metrics.get("stress_load", 0) > 0.6:
        evidence.append("発話パターンにストレス兆候を検出")
    if metrics.get("anxiety_uncertainty", 0) > 0.5:
        evidence.append("言い淀みや曖昧表現の増加")
    if metrics.get("cognitive_load", 0) > 0.6:
        evidence.append("発話の複雑さが低下傾向")
    if metrics.get("confidence_assertiveness", 0) < 0.4:
        evidence.append("声のトーンや発話速度に自信の低下を検出")
    if metrics.get("stability", 0) < 0.4:
        evidence.append("感情の変動が大きい")
    if metrics.get("stability", 0) > 0.7:
        evidence.append("安定した発話パターン")
    if metrics.get("confidence_assertiveness", 0) > 0.7:
        evidence.append("明確で自信のある発話")

    if not evidence:
        evidence.append("全体的に安定した状態")

    return evidence


def generate_individual_suggestion(metrics):
    """Generate suggestion based on metrics."""
    stress = metrics.get("stress_load", 0)
    anxiety = metrics.get("anxiety_uncertainty", 0)
    stability = metrics.get("stability", 0.5)

    if stress > 0.7:
        return "高いストレスレベルが検出されています。短い休憩を取ることをお勧めします。深呼吸や軽いストレッチが効果的です。"
    elif stress > 0.5:
        return "中程度のストレスが見られます。タスクを小さく分割し、優先順位を整理してみてください。"
    elif anxiety > 0.5:
        return "不安や迷いの兆候があります。必要に応じてサポートを求めることを検討してください。"
    elif stability < 0.4:
        return "感情の変動が見られます。自分のペースを大切にし、無理をしないようにしましょう。"
    else:
        return "良好な状態です。この調子を維持していきましょう。"


def clear_demo_data():
    """Clear all demo data created by this script."""
    frappe.flags.ignore_permissions = True

    print("🗑️ Clearing demo data...")

    # Delete in reverse order of dependencies
    for doctype in ["Voice Trigger Event", "Acoustic Statistics",
                    "Meeting Analysis Result", "Individual Analysis Result"]:
        count = frappe.db.count(doctype)
        frappe.db.delete(doctype)
        print(f"  Deleted {count} {doctype} records")

    # Delete sessions
    count = frappe.db.count("Voice Analysis Session")
    frappe.db.delete("Voice Analysis Session")
    print(f"  Deleted {count} Voice Analysis Session records")

    # Optionally delete demo users
    demo_emails = ["demo.user@example.com", "manager@example.com", "team.member@example.com"]
    for email in demo_emails:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True)
            print(f"  Deleted user: {email}")

    frappe.db.commit()
    print("✅ Demo data cleared!")


def get_demo_data_stats():
    """Get statistics about current demo data."""
    stats = {
        "sessions": frappe.db.count("Voice Analysis Session"),
        "individual_results": frappe.db.count("Individual Analysis Result"),
        "meeting_results": frappe.db.count("Meeting Analysis Result"),
        "trigger_events": frappe.db.count("Voice Trigger Event"),
        "acoustic_stats": frappe.db.count("Acoustic Statistics"),
        "monthly_reports": frappe.db.count("Monthly Report"),
    }
    return stats


def create_monthly_report_demo_data():
    """Create demo monthly reports for testing."""
    frappe.flags.ignore_permissions = True

    print("\n📊 Creating Monthly Report demo data...")

    from lifegence_industry.mind_analyzer.services.report_generator import ReportGeneratorService
    from frappe.utils import get_first_day, add_months, getdate

    # Get users with session data
    users = frappe.db.sql("""
        SELECT DISTINCT user
        FROM `tabVoice Analysis Session`
        WHERE status = 'Completed'
    """, as_dict=True)

    if not users:
        print("  ⚠️ No session data found. Run create_all_demo_data first.")
        return []

    generator = ReportGeneratorService()
    reports = []

    # Generate reports for each user
    for user_row in users:
        user = user_row.user

        # Get months with data for this user
        months = frappe.db.sql("""
            SELECT DISTINCT DATE_FORMAT(start_time, '%%Y-%%m-01') as month
            FROM `tabVoice Analysis Session`
            WHERE user = %s AND status = 'Completed'
            ORDER BY month DESC
            LIMIT 3
        """, (user,), as_dict=True)

        for month_row in months:
            month = month_row.month
            first_day = get_first_day(getdate(month))

            # Check if report already exists
            existing = frappe.db.exists("Monthly Report", {
                "user": user,
                "report_month": first_day
            })

            if existing:
                print(f"  ℹ️ Report already exists for {user} - {month}")
                continue

            try:
                report = generator.generate_report(user, str(first_day))
                reports.append(report)
                print(f"  ✅ Created report: {report.name}")
            except Exception as e:
                print(f"  ❌ Failed to create report for {user} - {month}: {str(e)}")

    frappe.db.commit()
    print(f"\n📊 Created {len(reports)} monthly reports")
    return reports


def create_full_demo_data_with_reports():
    """Create all demo data including monthly reports."""
    frappe.flags.ignore_permissions = True

    # First create session data
    sessions = create_all_demo_data()

    # Then create monthly reports
    reports = create_monthly_report_demo_data()

    print("\n" + "=" * 50)
    print("📋 Demo Data Summary:")
    stats = get_demo_data_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("=" * 50)

    return {"sessions": sessions, "reports": reports}


def clear_all_demo_data():
    """Clear all demo data including monthly reports."""
    frappe.flags.ignore_permissions = True

    print("🗑️ Clearing all demo data including monthly reports...")

    # Delete monthly reports first
    count = frappe.db.count("Monthly Report")
    frappe.db.delete("Monthly Report")
    print(f"  Deleted {count} Monthly Report records")

    # Then clear other demo data
    clear_demo_data()
