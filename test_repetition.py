# Copyright (c) 2022, Frappe Technologies and Contributors #
# See license.txt #

import frappe
from frappe.automation.doctype.repetition.repetition import (
	create_repeated_entries,
	get_repetition_entries,
)
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, getdate, today
from datetime import date

def add_custom_fields():
	df = dict(
		fieldname="repetition",
		label="Repetition",
		fieldtype="Link",
		insert_after="sender",
		options="Repetition",
		hidden=1,
		print_hide=1,
		read_only=1,
	)
	create_custom_field("ToDo", df)

class TestRepetition(FrappeTestCase):
	def setUp(self):
		if not frappe.db.sql(
			"SELECT `fieldname` FROM `tabCustom Field` WHERE `fieldname`='repetition' and `dt`=%s", "Todo"
		):
			add_custom_fields()

	def test_daily_repetition(self):
		# Returns a new Document object in memory which does not exist yet in the database.
		todo = frappe.get_doc(
			dict(doctype="ToDo", description="test recurring todo", assigned_by="Administrator")
		).insert()

		doc = make_repetition(doc_name=todo.name)
		# Unit testing to check the equality
		self.assertEqual(doc.next_schedule_date, today()) # ex. date(2022,10,10)
		data = get_repetition_entries(getdate(today())) # ex. date(2022,10,10)
		create_repeated_entries(data)
		# Commits current transaction.
		frappe.db.commit()

		todo = frappe.get_doc(doc.repeated_doctype, doc.doc_name)
		self.assertEqual(todo.repetition, doc.name)

		new_todo = frappe.db.get_value(
			"ToDo", {"repetition": doc.name, "name": ("!=", todo.name)}, "name"
		)

		new_todo = frappe.get_doc("ToDo", new_todo)

		self.assertEqual(todo.get("description"), new_todo.get("description"))

	def test_weekly_repetition(self):
		todo = frappe.get_doc(
			dict(doctype="ToDo", description="test weekly todo", assigned_by="Administrator")
		).insert()

		doc = make_repetition(
			repeated_doctype="ToDo",
			period_unit="Weekly",
			doc_name=todo.name,
			start_repetition_date=add_days(today(), -7), # ex. date(2022,10,10)
		)

		self.assertEqual(doc.next_schedule_date, date(2022,10,10))
		data = get_repetition_entries(getdate(today())) # ex. date(2022,10,10)
		create_repeated_entries(data)
		frappe.db.commit()

		todo = frappe.get_doc(doc.repeated_doctype, doc.doc_name)
		self.assertEqual(todo.repetition, doc.name)

		new_todo = frappe.db.get_value(
			"ToDo", {"repetition": doc.name, "name": ("!=", todo.name)}, "name"
		)

		new_todo = frappe.get_doc("ToDo", new_todo)

		self.assertEqual(todo.get("description"), new_todo.get("description"))

	def test_monthly_repetition(self):
		start_repetition_date = date(2022,10,10) #today() # ex. date(2022,10,10)
		def get_months(start, end):
			diff = (12 * end.year + end.month) - (12 * start.year + start.month)
			return diff + 1

		todo = frappe.get_doc(
			dict(
				doctype="ToDo", description="test monthly recurring todo", assigned_by="Administrator"
			)
		).insert()

		doc = make_repetition(
			repeated_doctype="ToDo",
			period_unit="Monthly",
			doc_name=todo.name,
			start_repetition_date=start_repetition_date,
		)

		data = get_repetition_entries(date(2022,10,10))#getdate(today())) # ex. date(2022,10,10)
		create_repeated_entries(data)
		docnames = frappe.get_all(doc.repeated_doctype, {"repetition": doc.name})
		self.assertEqual(len(docnames), 1)

		doc = frappe.get_doc("Repetition", doc.name)

		months = get_months(getdate(start_repetition_date), date(2022,10,10))#getdate(today())) # ex. date(2022,10,10)
		data = get_repetition_entries(date(2022,10,10))#getdate(today())) # ex. date(2022,10,10)
		create_repeated_entries(data)

		docnames = frappe.get_all(doc.repeated_doctype, {"repetition": doc.name})
		self.assertEqual(len(docnames), months)

	def test_get_next_schedule(self):
			current_date = date(2022,10,10)#getdate(today()) # ex. date(2022,10,10)
			todo = frappe.get_doc(
				dict(
					doctype="ToDo", description="test next schedule date for monthly", assigned_by="Administrator"
				)
			).insert()
			doc = make_repetition(
				period_unit="Monthly", doc_name=todo.name, start_repetition_date=add_months(today(), -2) # ex. date(2022,10,10)
			)

			# doc.next_schedule_date is set as on or after current date
			# it should not be a previous month's date
			self.assertTrue(doc.next_schedule_date >= current_date)

			todo = frappe.get_doc(
				dict(
					doctype="ToDo", description="test next schedule date for daily", assigned_by="Administrator"
				)
			).insert()
			doc = make_repetition(
				period_unit="Daily", doc_name=todo.name, start_repetition_date=add_days(today(), -2) # ex. date(2022,10,10)
			)
			self.assertEqual(getdate(doc.next_schedule_date), current_date)

def make_repetition(**args):
	args = frappe._dict(args)
	doc = frappe.get_doc(
		{
			"doctype": "Repetition",
			"repeated_doctype": args.repeated_doctype or "ToDo",
			"doc_name": args.doc_name or frappe.db.get_value("ToDo", "name"),
			"start_repetition_date": args.start_repetition_date or add_days(today(), -1), # ex. date(2022,10,10)
			"end_repetition_date": args.end_repetition_date or "",
			"period_unit":args.period_unit or "",
			"date_field": args.date_field or "start date",
			"repetition_period": args.repetition_period or 0,
		}
	).insert(ignore_permissions=True)

	return doc


