import frappe
from frappe import _

@frappe.whitelist()
def list():
    
    try:
        # Query the AGK_Rigs doctype
        dept = frappe.get_all(
            "AGK_Departments",
            fields=["department_name", "department_code", "primary_approver"]
        )
        # Return the result as JSON
        return (dept)

    except Exception as e:
        # Handle exceptions and return an error response
        frappe.throw(_("An error occurred while fetching rigs: {0}").format(str(e)))

@frappe.whitelist()
def approvers(department_name):
    try:
        # Fetch the department details matching the given department_name
        department = frappe.get_value(
            "AGK_Departments",
            {"department_name": department_name},
            ["primary_approver", "proxy_approver"],
            as_dict=True
        )

        # If no department is found, raise an error
        if not department:
            frappe.throw(_("No department found with the name: {0}").format(department_name))

        # Return the approvers' details
        return department
    except Exception as e:
        # Handle exceptions and return an error response
        frappe.throw(_("An error occurred while fetching approvers: {0}").format(str(e)))
