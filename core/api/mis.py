from frappe import get_all, get_doc
from frappe.utils.response import json_handler
import frappe
import json

@frappe.whitelist()
def list(is_product=None):
    
    try:
        # Build filters based on is_product argument
        filters = {}
        if is_product is not None:
            filters["is_product"] = int(is_product)  # Convert boolean to integer (0/1)

        # Fetch AGK_MIS records with optional filters
        agk_mis_records = get_all("AGK_MIS", fields=["name", "is_product", "mis_indicator"], filters=filters)

        # Include child table data (category and code fields only) for each record
        for record in agk_mis_records:
            doc = get_doc("AGK_MIS", record["name"])
            record["sub_categories"] = [
                {"category": child.get("category"), "code": child.get("code")}
                for child in doc.get("sub_categories", [])
            ]

        # Return the data as JSON
        return (agk_mis_records)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in get_agk_mis_with_children")
        frappe.throw(f"An error occurred: {str(e)}")
