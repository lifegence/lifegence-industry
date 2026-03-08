# Module Reference

This document provides detailed information on the three modules included in the **lifegence_industry** app.

**Table of Contents**

- [Medical Receipt (レセプト)](#medical-receipt)
- [Trade Management (貿易管理)](#trade-management)
- [Mind Analyzer (マインド分析)](#mind-analyzer)

---

## Medical Receipt

Medical receipt (診療報酬明細書) processing for healthcare facilities. This module handles patient encounters, automatic fee calculation, monthly receipt generation, validation, and CSV export for insurance claim submissions.

### DocTypes

| DocType                    | Type        | Description                                      |
|----------------------------|-------------|--------------------------------------------------|
| Medical Receipt Settings   | Single      | Clinic-level configuration                       |
| Patient Encounter          | Submittable | Individual patient visit record                  |
| Patient Insurance Info     | Standard    | Insurance details linked to a patient            |
| Encounter Service Line     | Child       | Service items within an encounter                |
| Encounter Diagnosis        | Child       | Diagnoses attached to an encounter               |
| Disease Master             | Standard    | Master list of diseases/conditions               |
| Medical Service Master     | Standard    | Master list of medical services and fee codes    |
| Fee Schedule Revision      | Standard    | Fee schedule versions with effective dates       |
| Receipt                    | Submittable | Generated monthly receipt for insurance claims   |
| Receipt Batch              | Standard    | Batch grouping of receipts for bulk submission   |
| Receipt Detail Line        | Child       | Individual line items within a receipt           |
| Receipt Validation Log     | Standard    | Validation check results for a receipt           |

### Workflow

```
Master Data Setup
  (Disease Master, Medical Service Master, Fee Schedule Revision)
        |
        v
Patient Insurance Info
  (Register patient insurance details)
        |
        v
Patient Encounter
  (Record visit with service lines and diagnoses)
        |
        v
Submit Encounter
  (Auto fee calculation triggered via on_submit hook)
        |
        v
Monthly Receipt Generation
  (Aggregate submitted encounters into receipts)
        |
        v
Receipt Validation
  (5 automated checks)
        |
        v
CSV Export
  (Generate formatted file for insurance submission)
```

**Step-by-step**:

1. **Set up master data.** Create Disease Master, Medical Service Master, and Fee Schedule Revision records. These are required for fee calculation.
2. **Register patient insurance.** Create Patient Insurance Info records linking patients to their insurance plans.
3. **Record patient encounters.** Create a Patient Encounter with Encounter Service Lines and Encounter Diagnoses.
4. **Submit the encounter.** On submission, the system automatically calculates fees using the active Fee Schedule Revision and the configured `point_unit_price`.
5. **Generate monthly receipts.** Use the receipt generation API to batch-create Receipt documents for all submitted encounters in a given month.
6. **Validate receipts.** Run validation to check for errors before submission. The system performs five checks:
   - Detail lines exist and are valid.
   - Diagnoses are present.
   - Insurance is active.
   - Insurance period covers the encounter date.
   - Points totals are consistent.
7. **Export to CSV.** Generate the submission file in the standard format (HE/RE/SI/SY/GO record structure).

### Scheduled Tasks

| Schedule             | Task                          | Description                               |
|----------------------|-------------------------------|-------------------------------------------|
| 5th of each month, 9 AM | `send_deadline_reminder`  | Email reminder for receipt submission deadline |

### API Reference

All endpoints are under `lifegence_industry.medical_receipt.api`.

**fee_calculation**

| Function                | Trigger / Usage                          | Description                                  |
|-------------------------|------------------------------------------|----------------------------------------------|
| `on_encounter_submit`   | Doc event: Patient Encounter `on_submit` | Calculates fees for a submitted encounter    |
| `calculate_fee`         | Whitelisted API                          | Manually trigger fee calculation             |

**receipt_generation**

| Function                      | Description                                          |
|-------------------------------|------------------------------------------------------|
| `generate_monthly_receipts`   | Generate Receipt documents for a given month         |
| `send_deadline_reminder`      | Scheduled task: send email reminder on the 5th       |

**receipt_validation**

| Function            | Description                                      |
|---------------------|--------------------------------------------------|
| `validate_receipt`  | Run all 5 validation checks on a Receipt         |

**receipt_export**

| Function             | Description                                      |
|----------------------|--------------------------------------------------|
| `export_receipt_csv` | Export receipt data in HE/RE/SI/SY/GO CSV format |

### CSV Export Format

The export produces a CSV with the following record types:

| Record Code | Name            | Content                              |
|-------------|-----------------|--------------------------------------|
| HE          | Header          | File metadata and clinic information |
| RE          | Receipt Common  | Receipt-level summary data           |
| SI          | Service Items   | Individual service line items        |
| SY          | Diagnoses       | Diagnosis codes and descriptions     |
| GO          | Footer          | Totals and file closing              |

### Pre-Installed Data

Medical Receipt Settings is **not** auto-created during install. You must configure it manually after installation.

---

## Trade Management

International trade and logistics management. This module covers the full shipment lifecycle from booking through customs clearance, including shipping documents, letters of credit, sanctions screening, and compliance checks.

### DocTypes

**Core**

| DocType                | Type        | Description                                   |
|------------------------|-------------|-----------------------------------------------|
| Trade Settings         | Single      | Module-level configuration                    |
| Trade Shipment         | Submittable | Central shipment record                       |
| Trade Shipment Item    | Child       | Items within a shipment                       |
| Trade Container        | Child       | Container details for a shipment              |
| Trade Charge           | Child       | Charges/costs associated with a shipment      |
| Trade Schedule         | Child       | Schedule milestones (ETD, ETA, etc.)          |
| Trade Document Link    | Child       | Links to related shipping documents           |

**Shipping Documents**

| DocType                  | Type     | Description                               |
|--------------------------|----------|-------------------------------------------|
| Bill of Lading           | Standard | Ocean shipping document                   |
| Air Waybill              | Standard | Air freight shipping document             |
| Commercial Invoice       | Standard | Trade invoice                             |
| Commercial Invoice Item  | Child    | Line items on a commercial invoice        |
| Packing List             | Standard | Packing details                           |
| Packing List Item        | Child    | Individual packing list entries           |
| Certificate of Origin    | Standard | Certificate of origin document            |
| COO Item                 | Child    | Items listed on a certificate of origin   |

**Customs**

| DocType                 | Type        | Description                                |
|-------------------------|-------------|--------------------------------------------|
| Customs Declaration     | Submittable | Import/Export/Re-Export/Re-Import declaration |
| Customs Declaration Item| Child       | Line items with HS codes and duty amounts  |
| Customs Tariff Rate     | Standard    | Tariff rate lookup by HS code              |
| Trade Compliance Check  | Standard    | Compliance verification record             |
| Compliance Match Entry  | Standard    | Individual match results from screening    |
| Sanctions List Entry    | Standard    | Entity in the sanctions/denied party list  |

**Finance**

| DocType          | Type     | Description                                      |
|------------------|----------|--------------------------------------------------|
| Letter of Credit | Standard | L/C lifecycle: Draft - Issued - Advised - Drawn - Expired |
| LC Amendment     | Standard | Amendments to an existing Letter of Credit       |

**Masters**

| DocType           | Type     | Description                          |
|-------------------|----------|--------------------------------------|
| Port Master       | Standard | Port/terminal reference data         |
| Vessel Master     | Standard | Vessel reference data                |
| Shipping Line     | Standard | Shipping company reference data      |
| Airline Master    | Standard | Airline reference data               |
| Freight Forwarder | Standard | Freight forwarder reference data     |
| Customs Broker    | Standard | Customs broker reference data        |

### Workflow

**Shipment Lifecycle**

```
Draft --> Booked --> Shipped --> In Transit --> Arrived --> Customs Cleared --> Delivered
```

**ERPNext Integration (Doc Events)**

| ERPNext DocType   | Event       | Action                                    |
|-------------------|-------------|-------------------------------------------|
| Sales Order       | `on_submit` | Auto-create export Trade Shipment         |
| Purchase Order    | `on_submit` | Auto-create import Trade Shipment         |
| Delivery Note     | `on_submit` | Update shipment status to Booked          |
| Purchase Receipt  | `on_submit` | Update shipment status to Delivered       |

Auto-creation is controlled by the `auto_create_shipment_from_so` and `auto_create_shipment_from_po` flags in Trade Settings.

**Letter of Credit Lifecycle**

```
Draft --> Issued --> Advised --> Drawn --> Expired
```

### Custom Fields on Item

The following fields are added to the standard ERPNext **Item** DocType under a "Trade / Export Control" section:

| Field Name               | Type  | Description                                    |
|--------------------------|-------|------------------------------------------------|
| `export_control_class`   | Data  | Export control classification (e.g., EAR99)    |
| `dual_use_flag`          | Check | Whether the item is classified as dual-use     |
| `catch_all_number`       | Data  | Japan METI catch-all control classification    |
| `export_license_required`| Check | Whether an export license is required          |

### Scheduled Tasks

| Schedule | Task                  | Description                                   |
|----------|-----------------------|-----------------------------------------------|
| Daily    | `check_eta_alerts`    | Send alerts for shipments arriving within 3 days |
| Daily    | `check_lc_expiry`     | Send alerts for L/Cs expiring within 14 days  |

### Services

**sanctions_screening**

Screen entities and shipments against the Sanctions List Entry database.

**schedule**

Daily scheduled checks for ETA proximity and L/C expiry notifications.

**hs_suggestion** (stub)

AI-assisted HS code suggestion based on item description. This feature is a placeholder for future implementation.

**document_check** (stub)

AI-assisted shipping document validation. This feature is a placeholder for future implementation.

### Reports

| Report                  | Description                                       |
|-------------------------|---------------------------------------------------|
| Customs Duty Report     | Summary of customs duties by declaration          |
| L/C Utilization         | Letter of credit usage and status tracking        |
| Trade Shipment Summary  | Overview of shipments by status, route, and period|

### Pre-Installed Data

- **Trade Settings** is auto-created with defaults: `auto_create_landed_cost = 1`, all other auto flags off.
- **Custom fields** on Item are auto-created during install.

---

## Mind Analyzer

Voice-based psychological analysis for workplace well-being. This module provides real-time voice analysis during individual sessions and meetings, detecting behavioral triggers and generating wellness reports.

### DocTypes

| DocType                    | Type     | Description                                      |
|----------------------------|----------|--------------------------------------------------|
| Voice Analyzer Settings    | Single   | Module-level configuration and API keys          |
| Voice Analysis Session     | Standard | Active or completed analysis session             |
| Individual Analysis Result | Standard | Metrics from an individual analysis session      |
| Meeting Analysis Result    | Standard | Metrics from a meeting analysis session          |
| Voice Trigger Event        | Standard | Detected behavioral trigger during a session     |
| Acoustic Statistics        | Standard | Raw acoustic measurements for a session segment  |
| Monthly Report             | Standard | Aggregated monthly wellness report               |

### Analysis Modes

**Individual Mode**

Analyzes a single person's voice. Produces the following metrics (each on a 0 to 1 scale):

| Metric                     | Description                                  |
|----------------------------|----------------------------------------------|
| `stress_load`              | Detected stress level                        |
| `anxiety_uncertainty`      | Anxiety and uncertainty indicators            |
| `cognitive_load`           | Mental processing burden                     |
| `confidence_assertiveness` | Confidence and assertiveness level           |
| `stability`                | Overall vocal stability                      |

**Meeting Mode**

Analyzes a group conversation. Produces the following metrics (each on a 0 to 1 scale):

| Metric               | Description                                        |
|-----------------------|----------------------------------------------------|
| `speak_up`           | Willingness to speak up                            |
| `respect_interaction`| Mutual respect in interactions                     |
| `error_tolerance`    | Tolerance for mistakes and differing views         |
| `power_balance`      | Balance of speaking power among participants       |
| `overall_ps`         | Overall psychological safety score                 |

### Trigger Types

The system detects 8 types of behavioral triggers during analysis:

| Trigger Type          | Description                                    | Default Threshold        |
|-----------------------|------------------------------------------------|--------------------------|
| `silence_spike`       | Unusually long silence                         | 3000 ms                  |
| `apology_phrase`      | Apology or self-diminishing phrases            | Per `trigger_threshold`  |
| `hedge_increase`      | Increase in hedge words (e.g., "maybe", "sort of") | 5 per minute        |
| `speech_rate_change`  | Sudden change in speaking speed                | 30% change               |
| `restart_increase`    | Frequent sentence restarts                     | 4 per minute             |
| `interruption`        | One speaker interrupting another               | Per `trigger_threshold`  |
| `overlap`             | Overlapping speech between speakers            | Per `trigger_threshold`  |
| `power_imbalance`     | Uneven distribution of speaking time           | Per `trigger_threshold`  |

### Workflow

```
Configure Voice Analyzer Settings
  (API keys, thresholds, modes)
        |
        v
Start Session (API call)
  (Individual or Meeting mode)
        |
        v
Analyze Audio (real-time API calls)
  (Audio segments sent at analysis_interval_sec intervals)
        |
        v
Trigger Detection
  (Voice Trigger Events created automatically)
        |
        v
End Session (API call)
  (Individual/Meeting Analysis Result generated)
        |
        v
Monthly Report Generation
  (Aggregated wellness score, trends, AI insights)
```

### Scheduled Tasks

| Schedule          | Task                       | Description                              |
|-------------------|----------------------------|------------------------------------------|
| Daily             | `cleanup_old_data`         | Delete data older than `data_retention_days` |
| Every 6 hours     | `cleanup_stale_sessions`   | Close sessions inactive for more than 24 hours |

### Pages

| Page                       | Description                                       |
|----------------------------|---------------------------------------------------|
| Mind Analyzer Dashboard    | Real-time session view and analysis controls       |
| Monthly Report Viewer      | View and browse monthly wellness reports           |
| Organization Dashboard     | Organization-wide analytics and trends             |

### Roles

| Role                   | Permissions                                       |
|------------------------|---------------------------------------------------|
| Mind Analyzer User     | Start/end own sessions, view own results          |
| Mind Analyzer Manager  | View team analysis results and department reports |
| Mind Analyzer Admin    | Configure settings, view all data                 |

### User Data Protection

The following DocTypes are registered for Frappe's user data protection framework:

- **Voice Analysis Session** -- filtered by `user` field
- **Individual Analysis Result** -- filtered by `owner`
- **Meeting Analysis Result** -- filtered by `owner`

This ensures compliance with data deletion and export requests.

### API Reference

All endpoints are under `lifegence_industry.mind_analyzer.api`.

**session**

| Function           | Description                                       |
|--------------------|---------------------------------------------------|
| `start_session`    | Start a new analysis session (individual or meeting) |
| `end_session`      | End an active session and generate results        |
| `cancel_session`   | Cancel a session without generating results       |
| `has_analyzer_access` | Permission check for app screen access         |

**analysis**

| Function           | Description                                       |
|--------------------|---------------------------------------------------|
| `analyze_audio`    | Process an audio segment in real-time             |

**reports**

| Function                  | Description                                   |
|---------------------------|-----------------------------------------------|
| `get_trend_data`          | Retrieve trend data for a user over time      |

**reports_monthly**

| Function                  | Description                                   |
|---------------------------|-----------------------------------------------|
| Monthly report endpoints  | Generate and retrieve monthly reports         |

**reports_department**

| Function                      | Description                               |
|-------------------------------|-------------------------------------------|
| Department analytics endpoints | Department-level aggregated analytics    |

**reports_summary / reports_team / reports_triggers / reports_export**

Additional reporting endpoints for organization-wide analytics, team views, trigger analysis, and data export.

### Services

| Service              | Description                                        |
|----------------------|----------------------------------------------------|
| `audio_processor`    | Process raw audio data into analyzable segments    |
| `trigger_detector`   | Detect behavioral triggers in audio data           |
| `individual_analyzer`| Generate Individual Analysis Result                |
| `meeting_analyzer`   | Generate Meeting Analysis Result                   |
| `gemini_service`     | Interface with Google Gemini API for AI analysis   |
| `realtime_service`   | Handle real-time session events and updates        |
| `report_generator`   | Generate Monthly Report documents                  |
| `cleanup_service`    | Data retention enforcement and stale session cleanup |

### Pre-Installed Data

- **Voice Analyzer Settings** is auto-created with defaults: `analysis_interval_sec = 10`, `trigger_threshold = 0.3`, `data_retention_days = 90`, both modes enabled.
- **Roles** (Mind Analyzer User, Manager, Admin) are auto-created.
