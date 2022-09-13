# Copyright (c) 2022, Frappe Technologies and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	getdate,
	today,
	month_diff,
	add_days,
	date_diff
)

from frappe.utils.background_jobs import get_jobs
month_map = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}

class Repetition(Document):
	# Controller hooks (method).
	def validate(self):
		self.validate_dates()
		self.update_repetition_id()
		self.get_period()
		self.set_next_schedule()
		# self.create_repeated()

	def after_save(self):
		frappe.get_doc(self.repeated_doctype, self.doc_name).notify_update()
		if self.end_repetition_date == self.start_repetition_date:
			frappe.throw(
				("{0} should not be same as {1}").format(frappe.bold("end date"), frappe.bold("start date"))
			)

	def on_trash(self):
		# Called if the document being deleted
		frappe.db.set_value(self.repeated_doctype, self.doc_name, "repetition", "")
		frappe.get_doc(self.repeated_doctype, self.doc_name).notify_update()

	def update_repetition_id(self):
		# check if document is already on repetition
		repetition = frappe.db.get_value(self.repeated_doctype, self.doc_name, "repetition")
		if repetition and repetition != self.name and not frappe.flags.in_patch:
			# Show dialog
			frappe.throw(
				_("The {0} is already on repetition {1}").format(self.doc_name, repetition)
			)
		else:
			frappe.db.set_value(self.repeated_doctype, self.doc_name, "repetition", self.name)

	def validate_dates(self):
		if frappe.flags.in_patch:
			return

		#Fetching posting date field | didn't work 
		#posting_date = frappe.db.get_value(self.repeated_doctype, self.doc_name, 'posting_date')

		# Validation to verify date sequence
		if self.end_repetition_date:
			if self.date_field == 'posting date':
				self.validate_from_to_dates(posting_date, "end_repetition_date")
			else:
				self.validate_from_to_dates("start_repetition_date", "end_repetition_date")

	def set_next_schedule(self):
		# Adding a hidden field to hold the date value to use it
		if self.date_field == "start date":
			self.next_schedule_date = self.get_schedule_date(schedule_date=self.start_repetition_date)
		#else:
			#posting date

	# To create new repeated Doc.
	def create_documents(self):
		try:
			new_doc = self.make_new_document()
		except Exception:
			error_log = self.log_error("Repetition failed")

	def make_new_document(self):
		reference_doc = frappe.get_doc(self.repeated_doctype, self.doc_name)
		# To get a copy of Doc.
		new_doc = frappe.copy_doc(reference_doc)
		self.update_document(new_doc, reference_doc)
		new_doc.insert(ignore_permissions=True)

		return new_doc

	def update_document(self, new_doc, reference_doc):
		
		if new_doc.meta.get_field("repetition"):
			new_doc.set("repetition", self.name)

		for fieldname in [
			"naming_series",
			"ignore_pricing_rule",
			"posting_time",
			"select_print_heading",
			"user_remark",
			"remarks",
			"owner",
		]:
			if new_doc.meta.get_field(fieldname):
				new_doc.set(fieldname, reference_doc.get(fieldname))

		for data in new_doc.meta.fields:
			if data.fieldtype == "Date" and data.reqd:
				new_doc.set(data.fieldname, self.next_schedule_date)

		repeated_doc = frappe.get_doc("Repetition", self.name)

		# for any action that needs to take place after the recurring document creation
		# on recurring method of that doctype is triggered
		new_doc.run_method("on_recurring", reference_doc=reference_doc, repeated_doc=repeated_doc)

	def get_schedule_date(self, schedule_date):
		start_date = self.set_dates()	
		if month_map.get(self.period_unit):
			let = month_diff(schedule_date, start_date)
			month_count = month_map.get(self.period_unit) + let - 1
		else:
			month_count = 0
		
		if month_count:
			next_date = get_next_date(self.start_repetition_date, month_count)
		else:
			days = self.get_days(schedule_date)
			next_date = add_days(schedule_date, days)

		if self.end_repetition_date:
			# next schedule date should be after or on current date
			while getdate(next_date) < getdate(today()) and getdate(next_date) < getdate(self.end_repetition_date): # ex. date(2022,10,10)
				if month_count:
					month_count += month_map.get(self.period_unit, 0)
					next_date = get_next_date(start_date, month_count, day_count)
				else:
					days = self.get_days(next_date)
					next_date = add_days(next_date, days)
		
		return next_date
		
	def get_period(self):
		# To set repetition_period value
		start_date = self.set_dates()
		end_date = self.end_repetition_date
		if end_date:
			if month_map.get(self.period_unit):
				let = month_diff(end_date, start_date)
				count = int((let - 1) / month_map.get(self.period_unit))
			elif month_map.get(self.period_unit):
				let = month_diff(end_date, start_date)
				count = int((let - 1) / month_map.get(self.period_unit))
			elif month_map.get(self.period_unit):
				let = month_diff(end_date, start_date)
				count = int((let - 1))
			else:
				let = date_diff(end_date, start_date)
				if self.period_unit == "Weekly":
					count = int(let / 7)
				else:
					count = int(let)
		else:
			count = int('0')
		# Auto return the repetition period. #didn't set the value!!#
		doc = frappe.get_doc("Repetition", self.name)
		frappe.db.set_value("Repetition", doc.name, "repetition_period", count)




	def get_days(self, schedule_date):
		if self.period_unit == "Weekly":
			days = 7
		else:
			# Daily frequency
			days = 1

		return days

	def set_dates(self):
		#didn't work!
		#posting_date = frappe.db.get_value(self.repeated_doctype, self.doc_name, 'posting_date')

		if self.date_field == 'posting date':
			if self.start_repetition_date:
				set_date = getdate(self.start_repetition_date)
			else:
				set_date = gatedate(posting_date)
		else:
			set_date = getdate(self.start_repetition_date)

		return set_date


	# #For testing purpose...		
	# def create_repeated(self): 
	# 	current_date = date(2022,10,10)#date.today()
	# 	schedule_date = getdate(self.next_schedule_date)
		
	# 	if current_date == schedule_date:
	# 		frappe.throw(_("{0} should").format(frappe.bold(schedule_date)))
	# 		schedule_date = self.get_schedule_date(schedule_date=schedule_date)
	# 		period = self.get_period()
	# 		frappe.throw(
	# 			("{0} should not be same as {1}").format(frappe.bold(schedule_date), frappe.bold(period))
	# 		)
	# 	else:
	# 		frappe.throw(_("Not equal document"))

def get_next_date(dt, mcount, day=None):
	dt = getdate(dt)
	dt += relativedelta(months=mcount, day=day)
	return dt

def make_repetition_entry():
	# To run it in the background
	enqueued_method = "frappe.automation.doctype.repetition.repetition.create_repeated_entries"
	jobs = get_jobs()

	if not jobs or enqueued_method not in jobs[frappe.local.site]:
		date = getdate(today()) #ex. date(2022,10,10)
		data = get_repetition_entries(date)
		frappe.enqueue(enqueued_method, data=data)

def create_repeated_entries(data):
	# If I have more than repeated doc
	for d in data:
		doc = frappe.get_doc("Repetition", d.name)

		current_date = getdate(today()) #ex. date(2022,10,10)
		schedule_date = getdate(doc.next_schedule_date)

		if schedule_date == current_date:
			doc.create_documents()
			schedule_date = doc.get_schedule_date(schedule_date=schedule_date)
			if schedule_date:
				frappe.db.set_value("Repetition", doc.name, "next_schedule_date", schedule_date)

def get_repetition_entries(date=None):
	# To fetch all records without applying permissions.
	if not date:
		date = getdate(today()) #ex. date(2022,10,10)
	return frappe.db.get_all(
		"Repetition", filters=[["next_schedule_date", "<=", date]]
	)

# To populatee data when the repeat button is clicked.
@frappe.whitelist()
def make_repetition(doctype, docname, period_unit, start_repetition_date=None, end_repetition_date=None):
	doc = frappe.new_doc('Repetition')
	doc.repeated_doctype = doctype
	doc.doc_name = docname
	doc.period_unit = period_unit
	if start_repetition_date:
		doc.start_repetition_date = start_repetition_date
	if end_repetition_date:
		doc.end_repetition_date = end_repetition_date
	doc.save() ## I have used before_Save method but it doesn't work
	return doc

# method for to fetch doctype record
@frappe.whitelist()
# decorator is used to validate and sanitize user inputs sent through API or client-side request to avoid possible SQLi.
@frappe.validate_and_sanitize_search_inputs
def get_allow_repetition_doctypes(doctype, txt, searchfield, start, page_len, filters):
	# Returns a list of all records of a DocType.
	res = frappe.db.get_all(
		"Property Setter",
		{
			"property": "allow_repetition",
			"value": "1",
		},
		["doc_type"],
	)
	docs = [r.doc_type for r in res]

	res = frappe.db.get_all(
		"DocType",
		{
			"allow_repetition": 1,
		},
		["name"],
	)
	docs += [r.name for r in res]
	docs = set(list(docs))

	return [[d] for d in docs]
