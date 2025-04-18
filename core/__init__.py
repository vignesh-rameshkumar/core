
__version__ = '1.1.2'

import frappe
from frappe import _
import json

@frappe.whitelist()
def get_roles(module=None):
    user = frappe.session.user

    # Get all roles of the current session user
    user_roles = frappe.get_roles(user)

    if module:
        module = module.strip().lower()
        normalized_roles = [role.lower() for role in user_roles]

        def has_role(role_name):
            return int(role_name in normalized_roles)

        role_flags = {
            "employee": has_role("employee"),
            "project_lead": has_role("project lead"),
            "proxy_project_lead": has_role("proxy project lead"),
            "department_lead": has_role("department lead"),
            "proxy_department_lead": has_role("proxy department lead"),
            f"{module}_fl": has_role(f"{module} fl"),
            f"{module}_pfl": has_role(f"{module} pfl"),
            f"{module}_admin": has_role(f"{module} admin"),
            "super_admin": has_role("super admin"),
        }
        return role_flags

    # Fetch user and employee info in fewer calls
    employee_info = frappe.db.get_value(
        "Employee", {"user_id": user}, ["employee_name", "department"], as_dict=True
    ) or {}

    user_info = frappe.db.get_value(
        "User", user, ["desk_theme", "user_image"], as_dict=True
    ) or {}

    return {
        "roles": user_roles,
        "employee_name": employee_info.get("employee_name"),
        "department": employee_info.get("department"),
        "desk_theme": user_info.get("desk_theme"),
        "user_image": user_info.get("user_image"),
    }

@frappe.whitelist()
def get_desk_data():
    cache_key = "desk_settings_cache"
    cached_data = frappe.cache().get_value(cache_key)

    if cached_data:
        return json.loads(cached_data)

    # Fetch Desk Settings and cache it
    config_doc = frappe.get_single("Desk Settings")
    config_data = config_doc.configuration or "{}"

    frappe.cache().set_value(cache_key, config_data)
    return json.loads(config_data)

def update_desk_cache(self, *args, **kwargs):
    cache_key = "desk_settings_cache"
    config_doc = frappe.get_single("Desk Settings")
    config_data = config_doc.configuration or "{}"
    frappe.cache().set_value(cache_key, config_data)


@frappe.whitelist()
def search(txt, limit=20):
    
    limit = int(limit)
    all_doctypes = frappe.get_all("DocType", filters={"istable": 0}, pluck="name")
    permitted_doctypes = []

    for doctype in all_doctypes:
        if frappe.has_permission(doctype):  # This defaults to checking for "read"
            if not txt or txt.lower() in doctype.lower():
                permitted_doctypes.append({"name": doctype})
            if len(permitted_doctypes) >= limit:
                break

    return permitted_doctypes
