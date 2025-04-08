
__version__ = '1.0.5'

import frappe
from frappe import _

@frappe.whitelist()
def get_roles(module):
    if not module:
        frappe.throw(_("Module is required"))

    # Normalize module name for role matching (e.g., Fleet → fleet)
    module = module.strip().lower()

    # Get all roles of the current session user
    user_roles = frappe.get_roles(frappe.session.user)
    normalized_roles = [role.lower() for role in user_roles]

    # Prepare the response structure
    role_flags = {
        "employee": int("employee" in normalized_roles),
        "project_lead": int("project lead" in normalized_roles),
        "proxy_project_lead": int("proxy project lead" in normalized_roles),
        "department_lead": int("department lead" in normalized_roles),
        "proxy_department_lead": int("proxy department lead" in normalized_roles),
        f"{module}_fl": int(f"{module} fl" in normalized_roles),
        f"{module}_pfl": int(f"{module} pfl" in normalized_roles),
        f"{module}_admin": int(f"{module} admin" in normalized_roles),
        "super_admin": int("super admin" in normalized_roles),
    }

    return role_flags
