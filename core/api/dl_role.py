import frappe
from frappe import _
from frappe.model.document import Document

def assign(doc, method):
    """
    Manage Department Head and Proxy Department Head roles dynamically based on department email fields.
    
    Rules:
    1. Roles are managed based on primary_approver and proxy_approver fields.
    2. Avoid duplicate assignments and unnecessary removals.
    3. Optimize checks for roles and department associations.
    """
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

    # Function to check if user is part of any other departments
    def is_user_in_other_departments(email):
        if not email:
            return False
        
        try:
            filters = [
                ['AGK_Departments', 'primary_approver', '=', email]
            ]
            proxy_filters = [
                ['AGK_Departments', 'proxy_approver', '=', email]
            ]
            other_departments = frappe.get_all(
                'AGK_Departments', 
                filters=filters,
                or_filters=proxy_filters
            )
            return len(other_departments) > 1  # More than current department
        except Exception as e:
            frappe.log_error(f"Error checking other departments for {email}: {str(e)}")
            return False

    # Function to manage role for a specific user
    def manage_department_role(email, role, old_email=None):
        if not email:
            # Remove role if email is blank and user is not in any other departments
            if old_email and not is_user_in_other_departments(old_email):
                remove_role(old_email, role)
            return

        # Add role if not already assigned
        if not frappe.db.exists('Has Role', {'parent': email, 'role': role}):
            add_role(email, role)

        # Remove old role if email changed and old user is not in any other departments
        if old_email and old_email != email and not is_user_in_other_departments(old_email):
            remove_role(old_email, role)

    # Manage Department Head Role
    manage_department_role(
        safe_get_email(doc, 'primary_approver'), 
        'Department Head', 
        safe_get_email(old_doc, 'primary_approver') if old_doc else None
    )

    # Manage Proxy Department Head Role
    manage_department_role(
        safe_get_email(doc, 'proxy_approver'), 
        'Proxy Department Head', 
        safe_get_email(old_doc, 'proxy_approver') if old_doc else None
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
