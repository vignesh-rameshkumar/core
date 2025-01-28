import frappe
from frappe import _

@frappe.whitelist()
def list():
    
    try:
        # Query the AGK_Rigs doctype
        rigs = frappe.get_all(
            "AGK_Rigs",
            filters={"status": "Active"},
            fields=["rig_name", "rig_code"]
        )
        # Return the result as JSON
        return (rigs)

    except Exception as e:
        # Handle exceptions and return an error response
        frappe.throw(_("An error occurred while fetching rigs: {0}").format(str(e)))
