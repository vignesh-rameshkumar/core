import frappe

def after_install():
    """Create roles if they do not exist."""
    roles_to_create = [
        "Automation User",
        "Admin",
        "Super Admin",
        "Proxy Project Lead",
        "Proxy Department Head"
    ]

    for role in roles_to_create:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role
            }).insert()