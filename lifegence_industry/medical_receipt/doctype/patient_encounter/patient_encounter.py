import frappe
from frappe.model.document import Document

from lifegence_industry.medical_receipt.utils import calculate_medical_totals


class PatientEncounter(Document):
	def validate(self):
		self.calculate_totals()

	def after_insert(self):
		if self.encounter_type == "オンライン":
			self._create_video_meeting()

	def on_submit(self):
		self.status = "Submitted"

	def on_cancel(self):
		self.status = "Cancelled"
		self._cancel_video_meeting()

	def _create_video_meeting(self):
		"""Auto-create Video Meeting for online encounters."""
		if not frappe.db.exists("DocType", "Video Meeting"):
			return  # lifegence_chat not installed

		from datetime import timedelta

		from frappe.utils import get_datetime

		encounter_dt = get_datetime(f"{self.encounter_date} 09:00:00")
		duration = 30

		meeting = frappe.new_doc("Video Meeting")
		meeting.title = f"オンライン診療 - {self.patient_name or self.name}"
		meeting.meeting_type = "Scheduled"
		meeting.access_type = "Private"
		meeting.organizer = self.owner
		meeting.scheduled_start = encounter_dt
		meeting.scheduled_end = encounter_dt + timedelta(minutes=duration)
		meeting.duration_minutes = duration
		meeting.max_participants = 3
		meeting.insert(ignore_permissions=True)

		self.db_set("video_meeting", meeting.name)
		self.db_set("meeting_url", meeting.meeting_url)

	def _cancel_video_meeting(self):
		"""Cancel linked Video Meeting when encounter is cancelled."""
		if not self.video_meeting:
			return
		if not frappe.db.exists("Video Meeting", self.video_meeting):
			return
		meeting = frappe.get_doc("Video Meeting", self.video_meeting)
		if meeting.status not in ("Ended", "Cancelled"):
			meeting.cancel_meeting()

	def calculate_totals(self):
		calculate_medical_totals(self, detail_field="services")
