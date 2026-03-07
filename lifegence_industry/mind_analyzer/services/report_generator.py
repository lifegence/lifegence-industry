# Copyright (c) 2026 Lifegence
# For license information, please see license.txt

"""
Monthly Report Generator Service
Aggregates monthly data and generates reports with AI insights
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter

import frappe
from frappe import _
from frappe.utils import (
    getdate, get_first_day, get_last_day, now_datetime,
    add_days, date_diff
)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


REPORT_SUMMARY_PROMPT = """あなたは心理的ウェルネスのコンサルタントです。
月次レポートのサマリーを作成してください。

【作成ガイドライン】
- 親しみやすく、励ましになるトーン
- 具体的なデータに基づく
- 否定的な表現は最小限に
- プライバシーに配慮（具体的な発言内容には言及しない）
- 200-300文字程度

【出力形式】
JSON形式で以下を出力:
{
  "summary": "月次サマリー文",
  "advice": "具体的なアドバイス（300-400文字）",
  "focus_areas": ["改善ポイント1", "改善ポイント2", "改善ポイント3"]
}"""


class ReportGeneratorService:
    """
    Service for generating monthly psychological analysis reports
    """

    def __init__(self):
        self.model = None
        self._initialize_gemini()

    def _initialize_gemini(self):
        """Initialize Gemini client"""
        if not GENAI_AVAILABLE:
            return

        try:
            from lifegence_mind_analyzer.mind_analyzer.doctype.voice_analyzer_settings.voice_analyzer_settings import VoiceAnalyzerSettings
            api_key = VoiceAnalyzerSettings.get_gemini_api_key()

            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            frappe.log_error(f"Failed to initialize Gemini for report: {str(e)}")

    def generate_report(self, user: str, report_month: str) -> "frappe._dict":
        """
        Generate a monthly report for a user

        Args:
            user: User email
            report_month: Month to report (YYYY-MM-DD, will use first day)

        Returns:
            Created Monthly Report document
        """
        first_day = get_first_day(getdate(report_month))
        last_day = get_last_day(first_day)

        # Check if report already exists
        existing = frappe.db.exists("Monthly Report", {
            "user": user,
            "report_month": first_day
        })
        if existing:
            frappe.throw(_("Report for this month already exists: {0}").format(existing))

        # Collect all data for the month
        data = self._collect_monthly_data(user, first_day, last_day)

        if data["total_sessions"] == 0:
            frappe.throw(_("No analysis data found for this month"))

        # Calculate metrics
        metrics = self._calculate_metrics(data)

        # Generate AI insights
        ai_insights = self._generate_ai_insights(data, metrics)

        # Prepare chart data
        chart_data = self._prepare_chart_data(data, first_day, last_day)

        # Create report document
        report = frappe.get_doc({
            "doctype": "Monthly Report",
            "user": user,
            "report_month": first_day,
            "status": "Published",
            "generated_at": now_datetime(),

            # Summary
            "total_sessions": data["total_sessions"],
            "total_analysis_time_minutes": data["total_duration_minutes"],
            "overall_trend": metrics["overall_trend"],

            # Individual metrics
            "avg_stress_load": metrics["avg_stress_load"],
            "avg_anxiety": metrics["avg_anxiety"],
            "avg_cognitive_load": metrics["avg_cognitive_load"],
            "avg_confidence": metrics["avg_confidence"],
            "avg_stability": metrics["avg_stability"],
            "stress_trend": metrics["stress_trend"],

            # Meeting metrics
            "meeting_count": data["meeting_count"],
            "avg_ps_score": metrics["avg_ps_score"],
            "avg_speak_up": metrics["avg_speak_up"],
            "avg_respect": metrics["avg_respect"],
            "avg_error_tolerance": metrics["avg_error_tolerance"],

            # Trigger analysis
            "total_triggers": data["total_triggers"],
            "most_common_trigger": metrics["most_common_trigger"],
            "high_severity_triggers": metrics["high_severity_triggers"],
            "trigger_trend": metrics["trigger_trend"],

            # AI insights
            "ai_summary": ai_insights.get("summary", ""),
            "ai_advice": ai_insights.get("advice", ""),
            "ai_focus_areas": json.dumps(ai_insights.get("focus_areas", []), ensure_ascii=False),

            # Chart data
            "daily_stress_data": json.dumps(chart_data["daily_stress"], ensure_ascii=False),
            "weekly_summary_data": json.dumps(chart_data["weekly_summary"], ensure_ascii=False),
            "trigger_breakdown_data": json.dumps(chart_data["trigger_breakdown"], ensure_ascii=False),
        })

        report.insert(ignore_permissions=True)
        frappe.db.commit()

        return report

    def _collect_monthly_data(
        self, user: str, first_day, last_day
    ) -> Dict:
        """Collect all analysis data for the month"""

        # Get sessions
        sessions = frappe.get_all(
            "Voice Analysis Session",
            filters={
                "user": user,
                "status": "Completed",
                "start_time": [">=", first_day],
                "end_time": ["<=", add_days(last_day, 1)]
            },
            fields=["name", "mode", "start_time", "end_time", "duration_seconds"]
        )

        session_names = [s.name for s in sessions]

        # Get individual analysis results
        individual_results = []
        if session_names:
            individual_results = frappe.get_all(
                "Individual Analysis Result",
                filters={"session": ["in", session_names]},
                fields=[
                    "name", "session", "timestamp",
                    "stress_load", "anxiety_uncertainty", "cognitive_load",
                    "confidence_assertiveness", "stability"
                ]
            )

        # Get meeting analysis results
        meeting_results = []
        if session_names:
            meeting_results = frappe.get_all(
                "Meeting Analysis Result",
                filters={"session": ["in", session_names]},
                fields=[
                    "name", "session", "timestamp",
                    "speak_up", "respect_interaction", "error_tolerance",
                    "power_balance", "overall_ps"
                ]
            )

        # Get trigger events
        triggers = []
        if session_names:
            triggers = frappe.get_all(
                "Voice Trigger Event",
                filters={"session": ["in", session_names]},
                fields=["name", "session", "timestamp", "trigger_type", "severity"]
            )

        # Calculate totals
        total_duration = sum(s.duration_seconds or 0 for s in sessions)
        individual_sessions = [s for s in sessions if s.mode == "Individual"]
        meeting_sessions = [s for s in sessions if s.mode == "Meeting"]

        return {
            "sessions": sessions,
            "individual_results": individual_results,
            "meeting_results": meeting_results,
            "triggers": triggers,
            "total_sessions": len(sessions),
            "individual_session_count": len(individual_sessions),
            "meeting_count": len(meeting_sessions),
            "total_duration_minutes": total_duration // 60,
            "total_triggers": len(triggers),
        }

    def _calculate_metrics(self, data: Dict) -> Dict:
        """Calculate aggregated metrics from collected data"""
        metrics = {}

        # Individual metrics
        ind_results = data["individual_results"]
        if ind_results:
            metrics["avg_stress_load"] = self._safe_avg([r.stress_load for r in ind_results])
            metrics["avg_anxiety"] = self._safe_avg([r.anxiety_uncertainty for r in ind_results])
            metrics["avg_cognitive_load"] = self._safe_avg([r.cognitive_load for r in ind_results])
            metrics["avg_confidence"] = self._safe_avg([r.confidence_assertiveness for r in ind_results])
            metrics["avg_stability"] = self._safe_avg([r.stability for r in ind_results])

            # Calculate stress trend (first half vs second half)
            sorted_results = sorted(ind_results, key=lambda x: x.timestamp)
            mid = len(sorted_results) // 2
            if mid > 0:
                first_half_stress = self._safe_avg([r.stress_load for r in sorted_results[:mid]])
                second_half_stress = self._safe_avg([r.stress_load for r in sorted_results[mid:]])
                if first_half_stress and second_half_stress:
                    diff = second_half_stress - first_half_stress
                    if diff < -0.1:
                        metrics["stress_trend"] = "Improving"
                    elif diff > 0.1:
                        metrics["stress_trend"] = "Worsening"
                    else:
                        metrics["stress_trend"] = "Stable"
                else:
                    metrics["stress_trend"] = "Stable"
            else:
                metrics["stress_trend"] = "Stable"
        else:
            metrics["avg_stress_load"] = None
            metrics["avg_anxiety"] = None
            metrics["avg_cognitive_load"] = None
            metrics["avg_confidence"] = None
            metrics["avg_stability"] = None
            metrics["stress_trend"] = None

        # Meeting metrics
        mtg_results = data["meeting_results"]
        if mtg_results:
            metrics["avg_ps_score"] = self._safe_avg([r.overall_ps for r in mtg_results])
            metrics["avg_speak_up"] = self._safe_avg([r.speak_up for r in mtg_results])
            metrics["avg_respect"] = self._safe_avg([r.respect_interaction for r in mtg_results])
            metrics["avg_error_tolerance"] = self._safe_avg([r.error_tolerance for r in mtg_results])
        else:
            metrics["avg_ps_score"] = None
            metrics["avg_speak_up"] = None
            metrics["avg_respect"] = None
            metrics["avg_error_tolerance"] = None

        # Trigger metrics
        triggers = data["triggers"]
        if triggers:
            trigger_types = [t.trigger_type for t in triggers]
            counter = Counter(trigger_types)
            metrics["most_common_trigger"] = counter.most_common(1)[0][0] if counter else None
            metrics["high_severity_triggers"] = len([t for t in triggers if (t.severity or 0) > 0.7])

            # Trigger trend (first half vs second half of month)
            sorted_triggers = sorted(triggers, key=lambda x: x.timestamp)
            mid = len(sorted_triggers) // 2
            if mid > 0:
                first_half = len(sorted_triggers[:mid])
                second_half = len(sorted_triggers[mid:])
                if second_half < first_half * 0.7:
                    metrics["trigger_trend"] = "Decreasing"
                elif second_half > first_half * 1.3:
                    metrics["trigger_trend"] = "Increasing"
                else:
                    metrics["trigger_trend"] = "Stable"
            else:
                metrics["trigger_trend"] = "Stable"
        else:
            metrics["most_common_trigger"] = None
            metrics["high_severity_triggers"] = 0
            metrics["trigger_trend"] = None

        # Overall trend
        trends = [
            metrics.get("stress_trend"),
            metrics.get("trigger_trend")
        ]
        improving = trends.count("Improving") + trends.count("Decreasing")
        worsening = trends.count("Worsening") + trends.count("Increasing")

        if improving > worsening:
            metrics["overall_trend"] = "Improving"
        elif worsening > improving:
            metrics["overall_trend"] = "Declining"
        else:
            metrics["overall_trend"] = "Stable"

        return metrics

    def _generate_ai_insights(self, data: Dict, metrics: Dict) -> Dict:
        """Generate AI insights using Gemini"""
        if not self.model:
            return self._fallback_insights(data, metrics)

        prompt = self._format_insights_prompt(data, metrics)

        try:
            response = self.model.generate_content(
                f"{REPORT_SUMMARY_PROMPT}\n\n{prompt}"
            )

            result = self._parse_json_response(response.text)
            if result:
                return result

        except Exception as e:
            frappe.log_error(f"AI insights generation failed: {str(e)}")

        return self._fallback_insights(data, metrics)

    def _format_insights_prompt(self, data: Dict, metrics: Dict) -> str:
        """Format prompt for AI insights"""
        return f"""【月次分析データ】

セッション数: {data["total_sessions"]}回
分析時間合計: {data["total_duration_minutes"]}分
個人セッション: {data["individual_session_count"]}回
ミーティング: {data["meeting_count"]}回

【個人分析指標（平均）】
- ストレス負荷: {self._format_percent(metrics.get("avg_stress_load"))}
- 不安・不確実性: {self._format_percent(metrics.get("avg_anxiety"))}
- 認知負荷: {self._format_percent(metrics.get("avg_cognitive_load"))}
- 自信・主張性: {self._format_percent(metrics.get("avg_confidence"))}
- 安定性: {self._format_percent(metrics.get("avg_stability"))}
- ストレス傾向: {metrics.get("stress_trend", "N/A")}

【ミーティング指標（平均）】
- 心理的安全性スコア: {self._format_percent(metrics.get("avg_ps_score"))}
- 発言の自由度: {self._format_percent(metrics.get("avg_speak_up"))}
- 対人尊重: {self._format_percent(metrics.get("avg_respect"))}
- 失敗許容度: {self._format_percent(metrics.get("avg_error_tolerance"))}

【トリガー分析】
- 検出数: {data["total_triggers"]}件
- 最頻出: {metrics.get("most_common_trigger", "なし")}
- 高深刻度: {metrics.get("high_severity_triggers", 0)}件
- 傾向: {metrics.get("trigger_trend", "N/A")}

上記データに基づいて、ユーザーへの月次サマリーとアドバイスを生成してください。"""

    def _fallback_insights(self, data: Dict, metrics: Dict) -> Dict:
        """Generate fallback insights without AI"""
        stress = metrics.get("avg_stress_load", 0.5) or 0.5
        stability = metrics.get("avg_stability", 0.5) or 0.5
        ps_score = metrics.get("avg_ps_score")

        # Generate summary
        if stress < 0.3 and stability > 0.7:
            summary = "今月は全体的に安定した状態を維持できました。ストレス管理が良好で、心理的な安定性も高い傾向です。"
        elif stress > 0.6:
            summary = "今月はストレスが高めの傾向が見られました。適切な休息やリフレッシュを心がけることをお勧めします。"
        else:
            summary = "今月は概ね安定した状態でした。一部でストレス兆候が見られましたが、全体的にはバランスが取れています。"

        # Generate advice
        advice_parts = []
        if stress > 0.5:
            advice_parts.append("定期的な休憩を取り、深呼吸やストレッチを取り入れてみてください")
        if stability < 0.5:
            advice_parts.append("一日の終わりに振り返りの時間を設けると、感情の安定に役立ちます")
        if ps_score and ps_score < 0.5:
            advice_parts.append("ミーティングでは、まず自分の意見を述べる前に深呼吸をすると落ち着いて発言できます")

        if not advice_parts:
            advice_parts.append("現在の良い状態を維持するために、規則正しい生活リズムを続けてください")

        advice = "。".join(advice_parts) + "。"

        # Generate focus areas
        focus_areas = []
        if stress > 0.5:
            focus_areas.append("ストレス軽減")
        if stability < 0.5:
            focus_areas.append("感情の安定化")
        if metrics.get("avg_confidence", 1) < 0.5:
            focus_areas.append("自信の向上")
        if ps_score and ps_score < 0.6:
            focus_areas.append("ミーティングでの発言")

        if not focus_areas:
            focus_areas = ["現状維持", "さらなる成長"]

        return {
            "summary": summary,
            "advice": advice,
            "focus_areas": focus_areas[:3]
        }

    def _prepare_chart_data(self, data: Dict, first_day, last_day) -> Dict:
        """Prepare data for charts"""
        # Daily stress data
        daily_stress = {}
        for result in data["individual_results"]:
            date_key = getdate(result.timestamp).strftime("%Y-%m-%d")
            if date_key not in daily_stress:
                daily_stress[date_key] = []
            daily_stress[date_key].append(result.stress_load or 0)

        daily_stress_chart = [
            {"date": date, "stress": round(sum(values) / len(values), 3)}
            for date, values in sorted(daily_stress.items())
        ]

        # Weekly summary
        weekly_summary = self._calculate_weekly_summary(data, first_day)

        # Trigger breakdown
        trigger_types = [t.trigger_type for t in data["triggers"]]
        trigger_breakdown = dict(Counter(trigger_types))

        return {
            "daily_stress": daily_stress_chart,
            "weekly_summary": weekly_summary,
            "trigger_breakdown": trigger_breakdown
        }

    def _calculate_weekly_summary(self, data: Dict, first_day) -> List[Dict]:
        """Calculate weekly summaries"""
        weeks = []
        current_week_start = first_day

        for week_num in range(5):  # Max 5 weeks in a month
            week_end = add_days(current_week_start, 6)

            # Filter results for this week
            week_individual = [
                r for r in data["individual_results"]
                if current_week_start <= getdate(r.timestamp) <= week_end
            ]
            week_meeting = [
                r for r in data["meeting_results"]
                if current_week_start <= getdate(r.timestamp) <= week_end
            ]

            if week_individual or week_meeting:
                weeks.append({
                    "week": week_num + 1,
                    "start_date": str(current_week_start),
                    "avg_stress": self._safe_avg([r.stress_load for r in week_individual]),
                    "avg_stability": self._safe_avg([r.stability for r in week_individual]),
                    "avg_ps_score": self._safe_avg([r.overall_ps for r in week_meeting]),
                    "session_count": len(set(r.session for r in week_individual + week_meeting))
                })

            current_week_start = add_days(week_end, 1)
            if current_week_start.month != first_day.month:
                break

        return weeks

    def _safe_avg(self, values: List) -> Optional[float]:
        """Calculate average, handling None values"""
        valid_values = [v for v in values if v is not None]
        if valid_values:
            return round(sum(valid_values) / len(valid_values), 3)
        return None

    def _format_percent(self, value: Optional[float]) -> str:
        """Format value as percentage string"""
        if value is None:
            return "N/A"
        return f"{value * 100:.1f}%"

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Parse JSON from Gemini response"""
        import re

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None


def generate_monthly_reports_for_all_users(report_month: str = None):
    """
    Scheduled job to generate monthly reports for all users

    Args:
        report_month: Month to generate (default: previous month)
    """
    from frappe.utils import add_months, get_first_day

    if not report_month:
        # Default to previous month
        report_month = get_first_day(add_months(getdate(), -1))

    first_day = get_first_day(getdate(report_month))

    # Get all users with completed sessions in the month
    users = frappe.db.sql("""
        SELECT DISTINCT user
        FROM `tabVoice Analysis Session`
        WHERE status = 'Completed'
        AND start_time >= %s
        AND start_time < %s
    """, (first_day, add_days(get_last_day(first_day), 1)), as_dict=True)

    generator = ReportGeneratorService()
    generated = 0
    errors = []

    for user_row in users:
        user = user_row.user
        try:
            # Check if report already exists
            existing = frappe.db.exists("Monthly Report", {
                "user": user,
                "report_month": first_day
            })
            if not existing:
                generator.generate_report(user, str(first_day))
                generated += 1
                frappe.db.commit()
        except Exception as e:
            errors.append(f"{user}: {str(e)}")
            frappe.db.rollback()

    frappe.log_error(
        f"Monthly reports generated: {generated}, Errors: {len(errors)}\n" +
        "\n".join(errors) if errors else "",
        "Monthly Report Generation"
    )

    return {"generated": generated, "errors": errors}
