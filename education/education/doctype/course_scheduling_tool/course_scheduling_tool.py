from datetime import datetime, timedelta
import calendar
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate

from education.education.utils import OverlapError

class CourseSchedulingTool(Document):
    @frappe.whitelist()
    def schedule_course(self, days):
        """Creates course schedules as per specified parameters"""

        course_schedules = []
        course_schedules_errors = []
        rescheduled = []
        reschedule_errors = []

        self.validate_mandatory(days)
        self.validate_date()

        date = self.start_date
        while date <= self.end_date:
            if calendar.day_name[getdate(date).weekday()] in days:
                course_schedule = frappe.new_doc("Course Schedule")
                course_schedule.course = self.course
                course_schedule.schedule_date = date
                course_schedule.from_time = self.from_time
                course_schedule.to_time = self.to_time
                try:
                    course_schedule.insert()
                except OverlapError:
                    course_schedules_errors.append(date)
                else:
                    course_schedules.append(course_schedule)
            date += timedelta(days=1)

        return dict(
            course_schedules=course_schedules,
            course_schedules_errors=course_schedules_errors,
            rescheduled=rescheduled,
            reschedule_errors=reschedule_errors,
        )

    def validate_mandatory(self, days):
        """Validates all mandatory fields"""
        if not days:
            frappe.throw(_("Please select at least one day to schedule the course."))
        fields = [
            "course",
            "room",
            "from_time",
            "to_time",
            "start_date",
            "end_date",
        ]
        for d in fields:
            if not self.get(d):
                frappe.throw(_("{0} is mandatory").format(self.meta.get_label(d)))

    def validate_date(self):
        """Validates if Start Date is greater than End Date"""
        if self.start_date > self.end_date:
            frappe.throw(_("Start Date cannot be greater than End Date."))
