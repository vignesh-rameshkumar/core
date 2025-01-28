# Copyright (c) 2025, Agnikul Cosmos Private Limited and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe

class AGK_Projects(Document):
    def before_insert(self):
        # Retrieve the value of the indicator field
        indicator = self.indicator

        # Initialize the code series
        code_series_start = 1
        existing_codes = []

        # Fetch the last code used in the Project Detail child table across all documents
        last_project = frappe.get_all(
            "AGK_Projects",
            fields=["name"],
            order_by="creation desc",
            limit=1
        )
        if last_project:
            last_doc = frappe.get_doc("AGK_Projects", last_project[0].name)
            for detail in last_doc.details:
                if detail.code.startswith("P"):
                    existing_codes.append(int(detail.code[1:]))

        # Determine the starting code number
        if existing_codes:
            code_series_start = max(existing_codes) + 1

        # Append values to the Project Detail child table
        code_counter = code_series_start
        if self.is_rig:
            rig_entries = [
				f"{indicator}-Instrumentation",
                f"{indicator}-Electrical",
                f"{indicator}-Plumbing",
				f"{indicator}-Structural",
                f"{indicator}-Civil",
                f"{indicator}-Pre-civil"
            ]
            for entry in rig_entries:
                self.append("details", {
                    "name1": entry,
                    "code": f"P{code_counter:04d}"
                })
                code_counter += 1

        if self.is_general:
            general_entry = f"General-{indicator}"
            self.append("details", {
                "name1": general_entry,
                "code": f"P{code_counter:04d}"
            })
            code_counter += 1

        if self.is_product:
            product_entries = [
                f"{indicator}-Design & Manufacturing",
                f"{indicator}-Testing"
            ]
            for entry in product_entries:
                self.append("details", {
                    "name1": entry,
                    "code": f"P{code_counter:04d}"
                })
                code_counter += 1
