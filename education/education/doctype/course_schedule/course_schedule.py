from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document


class CourseSchedule(Document):
    def validate(self):
        self.set_title()
        self.validate_dates()
        self.validate_times()
        self.validate_theory_practical_dates()

    def before_save(self):
        self.set_hex_color()

    def set_title(self):
        """Set document Title"""
        self.title = self.course

    def validate_dates(self):
        """Validates if Start Date and End Date are set correctly"""
        self.start_date = frappe.utils.getdate(self.start_date)
        self.end_date = frappe.utils.getdate(self.end_date)

        if self.start_date > self.end_date:
            frappe.throw(_("Start Date cannot be greater than End Date."))

    def validate_times(self):
        """Validates if from_time is greater than to_time"""
        if self.from_time > self.to_time:
            frappe.throw(_("From Time cannot be greater than To Time."))

    def validate_theory_practical_dates(self):
        """Validates theory and practical dates"""
        self.theory_start_date = frappe.utils.getdate(self.theory_start_date)
        self.theory_end_date = frappe.utils.getdate(self.theory_end_date)
        self.practical_start_date = frappe.utils.getdate(self.practical_start_date)
        self.practical_end_date = frappe.utils.getdate(self.practical_end_date)

        if self.theory_start_date and self.theory_end_date:
            if self.theory_start_date < self.start_date or self.theory_end_date > self.end_date:
                frappe.throw(_("Theory dates must be within the course dates."))

        if self.practical_start_date and self.practical_end_date:
            if self.practical_start_date < self.start_date or self.practical_end_date > self.end_date:
                frappe.throw(_("Practical dates must be within the course dates."))

        if self.theory_start_date and self.theory_end_date:
            if self.theory_start_date > self.theory_end_date:
                frappe.throw(_("Theory Start Date cannot be greater than Theory End Date."))

        if self.practical_start_date and self.practical_end_date:
            if self.practical_start_date > self.practical_end_date:
                frappe.throw(_("Practical Start Date cannot be greater than Practical End Date."))

    def set_hex_color(self):
        colors = {
            "blue": "#EDF6FD",
            "green": "#E4F5E9",
            "red": "#FFF0F0",
            "orange": "#FFF1E7",
            "yellow": "#FFF7D3",
            "teal": "#E6F7F4",
            "violet": "#F5F2FF",
            "cyan": "#E0F8FF",
            "amber": "#FCF3CF",
            "pink": "#FEEEF8",
            "purple": "#F9F0FF",
        }
        self.color = colors[self.class_schedule_color or "green"]
