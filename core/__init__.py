
__version__ = '1.1.5'

import frappe
from frappe import _
import json
from datetime import datetime
import re
from frappe.utils import now_datetime

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

        # New: if asking about the Fleet module, expose is_vehicle
        if module == "fleet":
            role_flags["is_vehicle"] = has_role("vehicle")

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

def custom_name(self, series_format: str):
    # Only run for new documents
    if not getattr(self, "__islocal", False):
        return  # Exit early if doc is not new

    """
    Sets a custom name on the doc based on the provided series format.
    Format example: "PV_MMYY_####", "PVS_MMYY_##", etc.
    - Counter resets every month.
    - Series format must contain a fixed prefix and hash placeholders for counter (e.g., ####).
    - MMYY is automatically replaced based on current date.
    """

    current_date = now_datetime()
    mmyy = current_date.strftime("%m%y")
    series_prefix = series_format.replace("MMYY", mmyy)

    match = re.match(r"(.+?)_#+$", series_prefix)
    if not match:
        frappe.throw("Invalid series format. Use format like 'PV_MMYY_####'.")

    prefix = match.group(1)
    hash_count = series_prefix.count("#")
    like_pattern = f"{prefix}_%"

    last_name = frappe.db.get_value(
        self.doctype,
        filters={"name": ["like", like_pattern]},
        fieldname="name",
        order_by="creation desc"
    )

    if last_name and last_name.startswith(prefix):
        last_counter_str = last_name.replace(f"{prefix}_", "")
        last_counter = int(last_counter_str) if last_counter_str.isdigit() else 0
    else:
        last_counter = 0

    new_counter = last_counter + 1
    padded_counter = str(new_counter).zfill(hash_count)

    self.name = f"{prefix}_{padded_counter}"
