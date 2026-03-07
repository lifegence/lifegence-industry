# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Session data export for external analysis.
"""

import frappe


@frappe.whitelist()
def export_session_data(session_id: str, format: str = "json"):
    """
    Export session data for external analysis

    Args:
        session_id: Session UUID
        format: Export format (json, csv)

    Returns:
        dict/str: Exported data
    """
    from lifegence_mind_analyzer.api.analysis import get_session_results

    data = get_session_results(session_id=session_id)

    if format == "csv":
        import csv
        import io

        output = io.StringIO()

        # Write results
        if data["results"]:
            writer = csv.DictWriter(output, fieldnames=data["results"][0].keys())
            writer.writeheader()
            writer.writerows(data["results"])

        return {
            "format": "csv",
            "data": output.getvalue()
        }

    return {
        "format": "json",
        "data": data
    }
