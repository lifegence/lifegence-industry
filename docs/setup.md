# Setup Guide

This guide walks through installing and configuring the **lifegence_industry** app, which provides three industry-specific modules for Frappe/ERPNext: Medical Receipt, Trade Management, and Mind Analyzer.

> **License**: This software is released under the [MIT License](../LICENSE).

## Prerequisites

| Requirement      | Version  |
|------------------|----------|
| Python           | 3.14+    |
| Frappe Framework | v16+     |
| ERPNext          | v16+     |

Ensure your Frappe Bench environment is set up and at least one site exists before proceeding.

## Installation

### 1. Get the App

```bash
bench get-app https://github.com/lifegence/lifegence-industry.git
```

### 2. Install on Your Site

```bash
bench --site your-site install-app lifegence_industry
```

### 3. Run Migrations

```bash
bench --site your-site migrate
```

The `after_install` hook automatically performs the following:

- Creates **Trade Settings** with default values.
- Adds custom fields on the **Item** DocType for export control classification (`export_control_class`, `dual_use_flag`, `catch_all_number`, `export_license_required`).
- Creates **Voice Analyzer Settings** with default values.
- Creates Mind Analyzer roles: **Mind Analyzer User**, **Mind Analyzer Manager**, **Mind Analyzer Admin**.

## Post-Install Setup

### Medical Receipt Module

1. Navigate to **Medical Receipt Settings** and fill in your clinic information:
   - `clinic_code` (7-digit code)
   - `clinic_name`
   - `clinic_prefecture` (select from 47 prefectures)
   - `default_insurance_type`
   - `point_unit_price` (defaults to 10, meaning 1 point = 10 yen)
   - `submission_method` (Electronic or Paper)
   - `submission_deadline_day` (defaults to 10th of the month)
2. Import or create **Disease Master** and **Medical Service Master** records.
3. Create **Fee Schedule Revision** entries so the system can calculate fees on encounter submission.

### Trade Management Module

1. Navigate to **Trade Settings** and configure:
   - Default Incoterms
   - Default customs broker and freight forwarder
   - Company importer/exporter codes
   - Toggle auto-creation flags (`auto_create_shipment_from_so`, `auto_create_shipment_from_po`, `auto_create_landed_cost`, `auto_compliance_check`)
2. Populate master data: **Port Master**, **Vessel Master**, **Shipping Line**, **Airline Master**, **Freight Forwarder**, **Customs Broker**.
3. If using sanctions screening, populate **Sanctions List Entry** records.
4. Verify that the custom fields appear on the **Item** DocType under the "Trade / Export Control" section.

### Mind Analyzer Module

1. Navigate to **Voice Analyzer Settings** and enter your **Gemini API key** (required for AI-powered analysis).
2. Optionally enter a **Google Speech API key** for enhanced speech-to-text.
3. Review and adjust the default thresholds:
   - `analysis_interval_sec` (default: 10)
   - `trigger_threshold` (default: 0.3)
   - `data_retention_days` (default: 90)
4. Assign roles to users:
   - **Mind Analyzer User** -- can use the analyzer for self-analysis.
   - **Mind Analyzer Manager** -- can view team analysis and reports.
   - **Mind Analyzer Admin** -- can configure analyzer settings.

## Optional Dependencies

| Dependency         | Required By     | Purpose                                    |
|--------------------|-----------------|--------------------------------------------|
| Google Gemini API  | Mind Analyzer   | AI-powered voice analysis and insights     |
| Google Speech API  | Mind Analyzer   | Enhanced speech-to-text (optional)         |

These are external API services. Configure their keys in **Voice Analyzer Settings**.

## Updating

To update to the latest version:

```bash
cd ~/frappe-bench
bench get-app --upgrade lifegence_industry
bench --site your-site migrate
```

After upgrading, verify that any new settings fields or master data requirements are addressed. Check the release notes for breaking changes.

## Next Steps

- [Module Reference](modules.md) -- detailed documentation for each module.
- [Configuration Reference](configuration.md) -- complete settings field reference.
- [Troubleshooting](troubleshooting.md) -- common issues and resolutions.
