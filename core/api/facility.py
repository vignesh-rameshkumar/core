import frappe
from frappe import _

@frappe.whitelist()
def list():
    
    try:
        # Query the AGK_Rigs doctype
        facility = frappe.get_all(
            "AGK_Facilities",
            filters={"status": "Active"},
            fields=["facility_name", "facility_code"]
        )
        # Return the result as JSON
        return (facility)

    except Exception as e:
        # Handle exceptions and return an error response
        frappe.throw(_("An error occurred while fetching rigs: {0}").format(str(e)))