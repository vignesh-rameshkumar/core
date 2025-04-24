
__version__ = '1.1.3'

import frappe
from frappe import _
import json
from datetime import datetime

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

    # Fetch employee details
    employee_info = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["employee_name", "department", "date_of_birth", "date_of_joining"],
        as_dict=True
    ) or {}

    # Fetch user info
    user_info = frappe.db.get_value(
        "User",
        user,
        ["desk_theme", "user_image"],
        as_dict=True
    ) or {}

    # Get today's date
    today = datetime.today().date()

    # Check for birthday and anniversary
    dob = employee_info.get("date_of_birth")
    doj = employee_info.get("date_of_joining")
    is_birthday = dob and dob.month == today.month and dob.day == today.day
    is_anniversary = doj and doj.month == today.month and doj.day == today.day

    return {
        "roles": user_roles,
        "employee_name": employee_info.get("employee_name"),
        "department": employee_info.get("department"),
        "desk_theme": user_info.get("desk_theme"),
        "user_image": user_info.get("user_image"),
        "is_birthday": is_birthday,
        "is_anniversary": is_anniversary,
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


def _cache_key(user):
    return f"doctype_list:{user}"

@frappe.whitelist()
def search(txt=None, limit=20):
    
    user = frappe.session.user
    cache = frappe.cache()
    cache_key = _cache_key(user)

    permitted = cache.get_value(cache_key)
    if permitted is None:
        all_dts = frappe.get_all(
            "DocType", filters={"istable": 0}, pluck="name"
        )
        permitted = [dt for dt in all_dts if frappe.has_permission(dt)]
        cache.set_value(cache_key, permitted)

    txt_lower = (txt or "").lower()
    result = []
    for dt in permitted:
        if not txt_lower or txt_lower in dt.lower():
            result.append({"name": dt})
            if len(result) >= int(limit):
                break

    return result

def invalidate_user_cache(doc, method):

    cache = frappe.cache()

    if doc.doctype == "Has Role":
        user = doc.parent
        cache.delete_value(_cache_key(user))
    elif doc.doctype == "DocPerm":
        users = frappe.get_all(
            "User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"
        )
        for user in users:
            cache.delete_value(_cache_key(user))