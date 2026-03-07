# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Re-export shim — preserves frappe.call() API paths after module split.

All report functions have been split into focused modules:
  - reports_summary: dashboard summary and recent triggers
  - reports_department: department-level analysis and comparison
  - reports_team: manager and organization team analysis
  - reports_triggers: trigger event analysis
  - reports_export: session data export
  - reports_monthly: monthly report CRUD and comparison
"""

# Summary
from lifegence_industry.mind_analyzer.api.reports_summary import (  # noqa: F401
    get_summary,
    get_recent_triggers,
)

# Department
from lifegence_industry.mind_analyzer.api.reports_department import (  # noqa: F401
    get_department_summary,
    get_department_timeseries,
    get_department_comparison,
)

# Team
from lifegence_industry.mind_analyzer.api.reports_team import (  # noqa: F401
    get_team_analysis,
    get_organization_team_analysis,
)

# Triggers
from lifegence_industry.mind_analyzer.api.reports_triggers import (  # noqa: F401
    get_trigger_analysis,
)

# Export
from lifegence_industry.mind_analyzer.api.reports_export import (  # noqa: F401
    export_session_data,
)

# Monthly
from lifegence_industry.mind_analyzer.api.reports_monthly import (  # noqa: F401
    get_my_monthly_reports,
    get_monthly_report_detail,
    get_latest_monthly_report,
    generate_monthly_report,
    get_available_report_months,
    compare_monthly_reports,
    _calc_percent_change,
)
