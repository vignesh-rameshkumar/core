import frappe

def create(doc, method):
    """Create roles before inserting a new AGK_ERP_Products document."""
    module_name = doc.module_name

    # Define role names
    roles = {
        "FL": f"{module_name} FL",
        "PFL": f"{module_name} PFL",
        "Admin": f"{module_name} Admin"
    }

    # Create roles if they do not exist
    for role_key, role_name in roles.items():
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1
            }).insert(ignore_permissions=True)
            frappe.msgprint(f"Role '{role_name}' created successfully.")

def assign(doc, method):
    """Assign roles to users before saving the AGK_ERP_Products document."""
    module_name = doc.module_name
    primary_fl_user = doc.primary_fl
    proxy_fl_user = doc.proxy_fl
    admin_user = doc.admin

    # Define role names
    roles = {
        "FL": f"{module_name} FL",
        "PFL": f"{module_name} PFL",
        "Admin": f"{module_name} Admin"
    }

    # Retrieve old document to compare changes
    old_doc = doc.get_doc_before_save() if doc.get_doc_before_save() else None

    # Function to safely get email from doc or old_doc
    def safe_get_email(doc, field):
        try:
            email = getattr(doc, field, None) or doc.get(field)
            return email.lower() if isinstance(email, str) else None
        except Exception as e:
            frappe.log_error(f"Error retrieving email for {field}: {str(e)}")
            return None

    # Function to check if user is part of any other modules
    def is_user_in_other_modules(email):
        if not email:
            return False
        
        try:
            filters = [
                ['AGK_ERP_Products', 'primary_fl', '=', email]
            ]
            proxy_filters = [
                ['AGK_ERP_Products', 'proxy_fl', '=', email]
            ]
            admin_filters = [
                ['AGK_ERP_Products', 'admin', '=', email]
            ]
            other_modules = frappe.get_all(
                'AGK_ERP_Products', 
                filters=filters,
                or_filters=proxy_filters + admin_filters
            )
            return len(other_modules) > 1  # More than current module
        except Exception as e:
            frappe.log_error(f"Error checking other modules for {email}: {str(e)}")
            return False

    # Function to manage role for a specific user
    def manage_module_role(email, role, old_email=None):
        if not email:
            # Remove role if email is blank and user is not in any other modules
            if old_email and not is_user_in_other_modules(old_email):
                remove_role(old_email, role)
            return

        # Add role if not already assigned
        if not frappe.db.exists('Has Role', {'parent': email, 'role': role}):
            add_role(email, role)

        # Remove old role if email changed and old user is not in any other modules
        if old_email and old_email != email and not is_user_in_other_modules(old_email):
            remove_role(old_email, role)

    # Manage FL Role
    manage_module_role(
        safe_get_email(doc, 'primary_fl'), 
        roles["FL"], 
        safe_get_email(old_doc, 'primary_fl') if old_doc else None
    )

    # Manage PFL Role
    manage_module_role(
        safe_get_email(doc, 'proxy_fl'), 
        roles["PFL"], 
        safe_get_email(old_doc, 'proxy_fl') if old_doc else None
    )

    # Manage Admin Role
    manage_module_role(
        safe_get_email(doc, 'admin'), 
        roles["Admin"], 
        safe_get_email(old_doc, 'admin') if old_doc else None
    )

def add_role(email, role):
    """Add role to user"""
    try:
        user = frappe.get_doc('User', email)
        user.append('roles', {'role': role})
        user.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error adding {role} to {email}: {str(e)}")

def remove_role(email, role):
    """Remove role from user"""
    try:
        user = frappe.get_doc('User', email)
        user.roles = [r for r in user.roles if r.role != role]
        user.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error removing {role} from {email}: {str(e)}")
