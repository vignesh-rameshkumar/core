# Copyright (c) 2025, Agnikul Cosmos Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AGK_MIS(Document):

    def before_insert(self):
        """
        Generate sequential codes for the 'sub_categories' child table.
        """
        if not self.sub_categories:
            return

        # Reset the counter for each new document
        counter = 1
        for row in self.sub_categories:
            # Generate the code as 'mis_indicator' + '01', '02', etc.
            row.code = f"{self.mis_indicator}{counter:02d}"
            counter += 1
        frappe.msgprint(counter)