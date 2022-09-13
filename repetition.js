// Copyright (c) 2022, Frappe Technologies and contributors
// For license information, please see license.txt

// To provide namespace
frappe.provide("frappe.repetition");

// Form scripts.
frappe.ui.form.on('Repetition', {
	// Event that triggered once when the form is created for the first time.
	setup: function (frm) {
		// Fetching the field's value by calling 'get_allow_repetition_doctypes' function.
		frm.fields_dict["repeated_doctype"].get_query = function () {
			return {
				query: "frappe.automation.doctype.repetition.repetition.get_allow_repetition_doctypes",
			};
		};

		frm.fields_dict["doc_name"].get_query = function () {
			return {
				filters: {
					repetition: "",
				},
			};
		};

		// fetching Date?
	},

	refresh: function(frm) {
		// View repetead document button if form hasn't been unchecked.
		if (!frm.is_dirty()) {
			let label = __("View {0}", [__(frm.doc.repeated_doctype)]);
			frm.add_custom_button(label, () =>
				frappe.set_route("List", frm.doc.repeated_doctype, { repetition: frm.doc.name })
			);
		};
	},


});
