# Troubleshooting

Common issues and resolutions for the **lifegence_industry** app. If your problem is not listed here, check the Frappe error log at **Help > Error Log** or the bench console output.

**Table of Contents**

- [Medical Receipt](#medical-receipt)
- [Trade Management](#trade-management)
- [Mind Analyzer](#mind-analyzer)
- [General](#general)

---

## Medical Receipt

### Receipt validation fails with "No detail lines"

**Symptom**: Validation check reports that the receipt has no detail lines.

**Cause**: The Patient Encounters included in the receipt did not have Encounter Service Lines, or the receipt generation did not pick up the expected encounters.

**Resolution**:
1. Open the related Patient Encounters and confirm that Encounter Service Lines exist and are filled in.
2. Verify that the encounters are in "Submitted" status.
3. Regenerate the receipt for the target month.

### Receipt validation fails with "No diagnoses"

**Symptom**: Validation reports missing diagnoses.

**Resolution**: Open the Patient Encounter(s) linked to the receipt and add at least one Encounter Diagnosis record. Then regenerate the receipt.

### Receipt validation fails with "Insurance not active" or "Insurance period mismatch"

**Symptom**: Validation reports that the patient's insurance is not active or does not cover the encounter date.

**Resolution**:
1. Open the **Patient Insurance Info** record for the affected patient.
2. Confirm the insurance status is active.
3. Confirm the insurance validity period covers the date of the Patient Encounter.
4. Correct the data and regenerate the receipt.

### Receipt validation fails with "Points inconsistency"

**Symptom**: The total points on the receipt do not match the sum of detail line points.

**Cause**: A fee calculation may have been updated after the receipt was generated, or a manual edit introduced an inconsistency.

**Resolution**:
1. Open the receipt and compare the header total with the sum of Receipt Detail Line points.
2. If the source encounters were modified after receipt generation, regenerate the receipt.

### Fee calculation returns zero or unexpected amounts

**Symptom**: After submitting a Patient Encounter, the calculated fee is zero or incorrect.

**Cause**: Missing or misconfigured fee schedule data.

**Resolution**:
1. Confirm that **Fee Schedule Revision** records exist and that at least one has an effective date on or before the encounter date.
2. Confirm that the **Medical Service Master** records referenced in the encounter's service lines have valid fee codes.
3. Check that `point_unit_price` in **Medical Receipt Settings** is set correctly (default is 10, meaning 1 point = 10 yen).
4. Review the error log for calculation exceptions.

### Deadline reminder email not received

**Symptom**: No email arrives on the 5th of the month.

**Resolution**:
1. Verify that the Frappe scheduler is running: `bench doctor` or check Scheduler Log.
2. Confirm email settings are configured in **Setup > Email Account**.
3. Check the error log for failures in `send_deadline_reminder`.

---

## Trade Management

### Trade Shipment not auto-created from Sales Order / Purchase Order

**Symptom**: Submitting a Sales Order or Purchase Order does not create a Trade Shipment.

**Cause**: The auto-creation flags are disabled by default.

**Resolution**:
1. Open **Trade Settings**.
2. Enable the relevant flag:
   - `auto_create_shipment_from_so` for Sales Orders.
   - `auto_create_shipment_from_po` for Purchase Orders.
3. Save the settings and try again.

### Shipment status not updating on Delivery Note / Purchase Receipt submit

**Symptom**: Submitting a Delivery Note or Purchase Receipt does not change the linked shipment status.

**Resolution**:
1. Verify that the Delivery Note or Purchase Receipt is linked to a Trade Shipment (check for a reference field or custom link).
2. Check the error log for exceptions in the doc event handlers (`delivery_note.on_submit` or `purchase_receipt.on_submit`).
3. Confirm that the Trade Shipment is not in a cancelled or completed state that prevents status changes.

### Sanctions screening returns no results

**Symptom**: Running a compliance check or sanctions screening finds no matches, even for known sanctioned entities.

**Cause**: The **Sanctions List Entry** DocType is empty.

**Resolution**:
1. Navigate to **Sanctions List Entry** in the Desk.
2. Import or manually create entries for the sanctions/denied party lists relevant to your business.
3. Re-run the screening after populating the data.

### Custom fields not appearing on Item DocType

**Symptom**: The "Trade / Export Control" section is not visible on Item records.

**Resolution**:
1. Run migrations to ensure custom fields are applied:
   ```bash
   bench --site your-site migrate
   ```
2. Clear the browser cache and reload the page.
3. If the fields still do not appear, run the install hook manually:
   ```bash
   bench --site your-site console
   ```
   ```python
   from lifegence_industry.install import after_install
   after_install()
   ```

### ETA alerts or L/C expiry notifications not sending

**Symptom**: No daily alert emails for approaching ETAs or expiring Letters of Credit.

**Resolution**:
1. Verify the scheduler is running.
2. Confirm that Trade Shipments have Schedule entries with ETA dates, and Letters of Credit have expiry dates set.
3. Check the error log for exceptions in `check_eta_alerts` or `check_lc_expiry`.

---

## Mind Analyzer

### Gemini API errors (authentication or quota)

**Symptom**: Analysis fails with an API error. Error log shows authentication failure or quota exceeded.

**Resolution**:
1. Open **Voice Analyzer Settings** and verify the `gemini_api_key` is correctly entered.
2. Confirm the API key is active and has not been revoked in the Google Cloud Console.
3. Check your Gemini API quota. If exceeded, wait for the quota to reset or request an increase.
4. Test the API key outside of the app to confirm it works.

### Session stuck in active state

**Symptom**: A Voice Analysis Session shows as active but is no longer being used. The dashboard shows a stale session.

**Cause**: The session was not properly ended (e.g., the user closed the browser without ending the session).

**Resolution**:
- **Automatic**: The system runs `cleanup_stale_sessions` every 6 hours, which closes sessions inactive for more than 24 hours.
- **Manual**: End the session via the API:
  ```python
  from lifegence_industry.mind_analyzer.api.session import end_session
  end_session(session_name="VOICE-SESSION-XXXXX")
  ```
  Or cancel it:
  ```python
  from lifegence_industry.mind_analyzer.api.session import cancel_session
  cancel_session(session_name="VOICE-SESSION-XXXXX")
  ```

### No audio data received during session

**Symptom**: A session is started but no analysis results are generated. The Acoustic Statistics records are empty.

**Resolution**:
1. Confirm the browser has microphone access permissions.
2. Check that the audio is being sent to the `analyze_audio` API endpoint at the configured interval (`analysis_interval_sec`).
3. Verify that the audio format is supported by the audio processor service.
4. Check the browser developer console for JavaScript errors on the Mind Analyzer Dashboard page.

### Monthly reports not generating

**Symptom**: No Monthly Report documents appear for the expected period.

**Resolution**:
1. Confirm that completed analysis sessions exist for the target month.
2. Trigger report generation manually via the API or the Monthly Report Viewer page.
3. Check the error log for exceptions in the `report_generator` service.

### Analysis results seem inaccurate

**Symptom**: Metric scores do not align with the perceived content of the conversation.

**Resolution**:
1. Review the **Voice Analyzer Settings** thresholds. The default `trigger_threshold` of 0.3 may be too sensitive or too lenient for your environment.
2. Adjust the advanced trigger thresholds (silence spike, hedge words, speech rate change, restart frequency) based on observed behavior.
3. Ensure audio quality is sufficient -- background noise, low microphone volume, or compression artifacts can affect analysis accuracy.
4. Check that the `analysis_interval_sec` is appropriate. Very short intervals may produce noisy results; very long intervals may miss transient events.

---

## General

### Data retention and cleanup

The Mind Analyzer module automatically deletes analysis data older than the configured `data_retention_days` (default: 90 days). This runs as a daily scheduled task.

To adjust the retention period:
1. Open **Voice Analyzer Settings**.
2. Change `data_retention_days` to the desired value.
3. Save.

Data removed by cleanup includes Voice Analysis Sessions, Individual/Meeting Analysis Results, Voice Trigger Events, and Acoustic Statistics older than the threshold.

### Scheduler not running

If scheduled tasks across all modules are not executing:

1. Check scheduler status:
   ```bash
   bench doctor
   ```
2. Ensure the scheduler is enabled for your site:
   ```bash
   bench --site your-site enable-scheduler
   ```
3. Verify that background workers are running:
   ```bash
   bench --site your-site scheduler status
   ```

### Permissions errors

If users receive "Permission Denied" errors:

1. Check that the user has the required roles assigned (see [Configuration Reference](configuration.md#role-assignments)).
2. For Mind Analyzer, verify that the user has at least the **Mind Analyzer User** role.
3. Review DocType permissions in **Setup > Role Permissions Manager** and adjust as needed.
