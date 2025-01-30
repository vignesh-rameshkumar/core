import frappe

def create_roles():
    """Create roles if they do not exist."""
    roles_to_create = [
        "Automation User",
        "Super Admin",
        "Project Lead",
        "Department Lead",
        "Proxy Project Lead",
        "Proxy Department Lead"
    ]

    # Declare Doctypes
    doctypes = [
        "AGK_Projects",
        "AGK_Departments",
        "AGK_Facilities",
        "AGK_ERP_Products",
        "AGK_Rigs",
        "AGK_MIS"
    ]

    for role in roles_to_create:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role
            }).insert()
            print(f"\033[93mRole '{role}' created successfully.\033[0m")

    # Assign permissions
    for doctype in doctypes:
        # Read access for Employee role
        if not frappe.db.exists("DocPerm", {"parent": doctype, "role": "Employee"}):
            frappe.get_doc({
                "doctype": "DocPerm",
                "parent": doctype,
                "parenttype": "DocType",
                "role": "Employee",
                "read": 1,
                "select": 1
            }).insert()
            print(f"\033[93mRead access assigned to 'Employee' role for Doctype '{doctype}'.\033[0m")

        # Full access for Automation User role
        if not frappe.db.exists("DocPerm", {"parent": doctype, "role": "Automation User"}):
            frappe.get_doc({
                "doctype": "DocPerm",
                "parent": doctype,
                "parenttype": "DocType",
                "role": "Automation User",
                "read": 1,
                "write": 1,
                "create": 1,
                "select": 1
            }).insert()
            print(f"\033[93mFull access assigned to 'Automation User' role for Doctype '{doctype}'.\033[0m")
    
    print("\033[92mThanks for installing Agnikul's Core App!\033[0m")

    # Declare Doctypes
    doctypes = [
        "AGK_Projects",
        "AGK_Departments",
        "AGK_Facilities",
        "AGK_ERP_Products",
        "AGK_Rigs",
        "AGK_MIS"
    ]

    # Assign permissions
    for doctype in doctypes:
        # Read access for Employee role
        if not frappe.db.exists("DocPerm", {"parent": doctype, "role": "Employee"}):
            frappe.get_doc({
                "doctype": "DocPerm",
                "parent": doctype,
                "role": "Employee",
                "read": 1,
                "select": 1
            }).insert()

        # Full access for Automation User role
        if not frappe.db.exists("DocPerm", {"parent": doctype, "role": "Automation User"}):
            frappe.get_doc({
                "doctype": "DocPerm",
                "parent": doctype,
                "role": "Automation User",
                "read": 1,
                "write": 1,
                "create": 1,
                "select": 1
            }).insert()
