"""
Monthly Report DocType
Stores monthly psychological analysis reports for users.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_first_day, get_last_day, nowdate
import json


class MonthlyReport(Document):
    def validate(self):
        self.validate_report_month()
        self.validate_metrics()
        self.validate_json_fields()

    def validate_report_month(self):
        """Ensure report_month is the first day of a month."""
        if self.report_month:
            report_date = getdate(self.report_month)
            first_day = get_first_day(report_date)
            if report_date != first_day:
                self.report_month = first_day

    def validate_metrics(self):
        """Ensure all metrics are within valid range (0-1)."""
        metric_fields = [
            "avg_stress_load", "avg_anxiety", "avg_cognitive_load",
            "avg_confidence", "avg_stability", "avg_ps_score",
            "avg_speak_up", "avg_respect", "avg_error_tolerance"
        ]
        for field in metric_fields:
            value = getattr(self, field, None)
            if value is not None:
                if value < 0:
                    setattr(self, field, 0.0)
                elif value > 1:
                    setattr(self, field, 1.0)

    def validate_json_fields(self):
        """Validate JSON fields are properly formatted."""
        json_fields = ["daily_stress_data", "weekly_summary_data", "trigger_breakdown_data", "ai_focus_areas"]
        for field in json_fields:
            value = getattr(self, field, None)
            if value:
                try:
                    json.loads(value)
                except json.JSONDecodeError:
                    frappe.throw(f"Invalid JSON in field: {field}")

    def before_save(self):
        """Calculate overall score before saving."""
        if not self.overall_score:
            self.calculate_overall_score()

    def calculate_overall_score(self):
        """Calculate composite wellness score (0-100)."""
        scores = []

        # Individual metrics (inverted where lower is better)
        if self.avg_stress_load is not None:
            scores.append((1 - self.avg_stress_load) * 100)
        if self.avg_anxiety is not None:
            scores.append((1 - self.avg_anxiety) * 100)
        if self.avg_cognitive_load is not None:
            scores.append((1 - self.avg_cognitive_load) * 100)
        if self.avg_confidence is not None:
            scores.append(self.avg_confidence * 100)
        if self.avg_stability is not None:
            scores.append(self.avg_stability * 100)

        # Meeting metrics
        if self.avg_ps_score is not None:
            scores.append(self.avg_ps_score * 100)

        if scores:
            self.overall_score = sum(scores) / len(scores)
        else:
            self.overall_score = 0

    def as_dict_for_report(self):
        """Return formatted dict for report display."""
        return {
            "user": self.user,
            "user_full_name": frappe.db.get_value("User", self.user, "full_name"),
            "report_month": str(self.report_month),
            "report_month_display": getdate(self.report_month).strftime("%Y年%m月"),
            "status": self.status,
            "generated_at": str(self.generated_at) if self.generated_at else None,

            # Summary
            "overall_score": round(self.overall_score or 0, 1),
            "overall_trend": self.overall_trend,
            "total_sessions": self.total_sessions or 0,
            "total_analysis_time_minutes": self.total_analysis_time_minutes or 0,

            # Individual metrics
            "individual_metrics": {
                "avg_stress_load": round((self.avg_stress_load or 0) * 100, 1),
                "avg_anxiety": round((self.avg_anxiety or 0) * 100, 1),
                "avg_cognitive_load": round((self.avg_cognitive_load or 0) * 100, 1),
                "avg_confidence": round((self.avg_confidence or 0) * 100, 1),
                "avg_stability": round((self.avg_stability or 0) * 100, 1),
                "stress_trend": self.stress_trend,
            },

            # Meeting metrics
            "meeting_metrics": {
                "meeting_count": self.meeting_count or 0,
                "avg_ps_score": round((self.avg_ps_score or 0) * 100, 1),
                "avg_speak_up": round((self.avg_speak_up or 0) * 100, 1),
                "avg_respect": round((self.avg_respect or 0) * 100, 1),
                "avg_error_tolerance": round((self.avg_error_tolerance or 0) * 100, 1),
            },

            # Trigger analysis
            "trigger_analysis": {
                "total_triggers": self.total_triggers or 0,
                "most_common_trigger": self.most_common_trigger,
                "high_severity_triggers": self.high_severity_triggers or 0,
                "trigger_trend": self.trigger_trend,
            },

            # AI insights
            "ai_insights": {
                "summary": self.ai_summary,
                "advice": self.ai_advice,
                "focus_areas": json.loads(self.ai_focus_areas) if self.ai_focus_areas else [],
            },

            # Chart data
            "chart_data": {
                "daily_stress": json.loads(self.daily_stress_data) if self.daily_stress_data else [],
                "weekly_summary": json.loads(self.weekly_summary_data) if self.weekly_summary_data else [],
                "trigger_breakdown": json.loads(self.trigger_breakdown_data) if self.trigger_breakdown_data else {},
            }
        }

    @staticmethod
    def get_report_for_user(user, report_month):
        """Get or create a report for a specific user and month."""
        first_day = get_first_day(getdate(report_month))

        existing = frappe.db.exists("Monthly Report", {
            "user": user,
            "report_month": first_day
        })

        if existing:
            return frappe.get_doc("Monthly Report", existing)
        return None

    @staticmethod
    def get_user_reports(user, limit=12):
        """Get recent reports for a user."""
        reports = frappe.get_all(
            "Monthly Report",
            filters={"user": user, "status": "Published"},
            fields=["name", "report_month", "overall_score", "overall_trend", "status"],
            order_by="report_month desc",
            limit=limit
        )
        return reports
