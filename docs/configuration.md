# Configuration Reference

Complete reference for all configurable settings in the **lifegence_industry** app. Each module has a dedicated Settings DocType accessible from the Frappe Desk.

**Table of Contents**

- [Medical Receipt Settings](#medical-receipt-settings)
- [Trade Settings](#trade-settings)
- [Voice Analyzer Settings](#voice-analyzer-settings)
- [Role Assignments](#role-assignments)

---

## Medical Receipt Settings

**DocType**: Medical Receipt Settings (Single)

**Path**: Medical Receipt Settings

| Field                    | Type      | Default          | Description                                                     |
|--------------------------|-----------|------------------|-----------------------------------------------------------------|
| `clinic_code`            | Data      | --               | 7-digit clinic identification code                              |
| `clinic_name`            | Data      | --               | Name of the healthcare facility                                 |
| `clinic_prefecture`      | Select    | --               | Prefecture where the clinic is located (47 options)             |
| `default_insurance_type` | Select    | --               | Default insurance type for new encounters                       |
| `point_unit_price`       | Currency  | 10               | Yen value per point (1 point = this value in yen)               |
| `submission_method`      | Select    | --               | Receipt submission method                                       |
| `submission_deadline_day`| Int       | 10               | Day of month for submission deadline                            |
| `auto_validate_on_generate` | Check | 0                | Automatically run validation when generating receipts           |

**Insurance Type Options**

| Value                | Japanese            |
|----------------------|---------------------|
| Social               | 社会保険            |
| National             | 国民健康保険        |
| Late-Stage Elderly   | 後期高齢者医療      |
| Public Expense       | 公費                |
| Self-Pay             | 自費                |

**Submission Method Options**

| Value       | Description                    |
|-------------|--------------------------------|
| Electronic  | Electronic filing (電子請求)   |
| Paper       | Paper filing (紙請求)          |

---

## Trade Settings

**DocType**: Trade Settings (Single)

**Path**: Trade Settings

### General

| Field                         | Type    | Default | Description                                          |
|-------------------------------|---------|---------|------------------------------------------------------|
| `default_incoterms`           | Link    | --      | Default Incoterms for new shipments                  |
| `default_customs_broker`      | Link    | --      | Default Customs Broker for declarations              |
| `default_freight_forwarder`   | Link    | --      | Default Freight Forwarder for shipments              |
| `company_importer_code`       | Data    | --      | Company's importer registration code                 |
| `company_exporter_code`       | Data    | --      | Company's exporter registration code                 |

### Automation Flags

| Field                           | Type  | Default | Description                                        |
|---------------------------------|-------|---------|----------------------------------------------------|
| `auto_create_shipment_from_so`  | Check | 0       | Auto-create export shipment on Sales Order submit  |
| `auto_create_shipment_from_po`  | Check | 0       | Auto-create import shipment on Purchase Order submit |
| `auto_create_landed_cost`       | Check | 1       | Auto-create landed cost voucher from shipment charges |
| `auto_compliance_check`         | Check | 0       | Auto-run compliance check on shipment creation     |

### AI Features (Stubs)

| Field                         | Type  | Default | Description                                    |
|-------------------------------|-------|---------|-------------------------------------------------|
| `enable_ai_hs_suggestion`     | Check | 0       | Enable AI-assisted HS code suggestion (future) |
| `enable_ai_document_check`    | Check | 0       | Enable AI-assisted document validation (future)|

---

## Voice Analyzer Settings

**DocType**: Voice Analyzer Settings (Single)

**Path**: Voice Analyzer Settings

### API Keys

| Field                  | Type     | Required | Description                                  |
|------------------------|----------|----------|----------------------------------------------|
| `gemini_api_key`       | Password | Yes      | Google Gemini API key for AI analysis        |
| `google_speech_api_key`| Password | No       | Google Speech API key for speech-to-text     |

### General Settings

| Field                    | Type  | Default | Description                                        |
|--------------------------|-------|---------|----------------------------------------------------|
| `analysis_interval_sec`  | Int   | 10      | Seconds between audio analysis cycles              |
| `trigger_threshold`      | Float | 0.3     | Base sensitivity threshold for trigger detection (0-1) |
| `data_retention_days`    | Int   | 90      | Days to retain analysis data before cleanup        |
| `enable_individual_mode` | Check | 1       | Enable individual (single-person) analysis mode    |
| `enable_meeting_mode`    | Check | 1       | Enable meeting (group) analysis mode               |

### Advanced Trigger Thresholds

These thresholds control the sensitivity of individual trigger types. Adjust them to reduce false positives or increase detection sensitivity for your environment.

| Field                              | Type  | Default | Unit     | Description                              |
|------------------------------------|-------|---------|----------|------------------------------------------|
| `silence_spike_threshold_ms`       | Int   | 3000    | ms       | Minimum silence duration to flag         |
| `hedge_words_per_min_threshold`    | Int   | 5       | per min  | Hedge word frequency to trigger alert    |
| `speech_rate_change_pct_threshold` | Int   | 30      | %        | Percent change in speech rate to flag    |
| `restart_per_min_threshold`        | Int   | 4       | per min  | Sentence restart frequency to flag       |

---

## Role Assignments

### Mind Analyzer Roles

These roles are created automatically during installation. Assign them to users via **Setup > User > Roles**.

| Role                   | Desk Access | Description                                       |
|------------------------|-------------|---------------------------------------------------|
| Mind Analyzer User     | Yes         | Can use voice analyzer for self-analysis          |
| Mind Analyzer Manager  | Yes         | Can view team analysis and reports                |
| Mind Analyzer Admin    | Yes         | Can configure voice analyzer settings             |

**Recommended assignment**:

| User Type          | Roles to Assign                                    |
|--------------------|----------------------------------------------------|
| Regular employee   | Mind Analyzer User                                 |
| Team leader        | Mind Analyzer User, Mind Analyzer Manager          |
| HR / Administrator | Mind Analyzer User, Mind Analyzer Manager, Mind Analyzer Admin |

### Medical Receipt and Trade Management Roles

These modules use standard ERPNext roles. Ensure users have the appropriate permissions:

| Module            | Relevant ERPNext Roles                              |
|-------------------|-----------------------------------------------------|
| Medical Receipt   | Healthcare Practitioner, Healthcare Administrator   |
| Trade Management  | Purchase User, Purchase Manager, Sales User, Sales Manager, Accounts User |

Adjust DocType permissions as needed for your organization through **Setup > Role Permissions Manager**.
