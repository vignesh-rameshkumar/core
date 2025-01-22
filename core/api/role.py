import frappe
from frappe import _
from frappe.model.document import Document

def pl(doc, method):
    """
    Manage Project Lead and Proxy Project Lead roles dynamically based on project status and email fields.
    
    Rules:
    1. Roles are only managed when project status is Active
    2. Avoid duplicate assignments and unnecessary removals
    3. Optimize checks for roles and project associations
    """
    # Retrieve old document to compare changes
    old_doc = doc.get_doc_before_save() if doc.get_doc_before_save() else None

    # Function to safely get email from doc or old_doc
    def safe_get_email(doc, field):
        try:
            # Log the entire document and field for debugging
            frappe.log_error(f"Debugging email retrieval for {field}: {doc}")
            
            # Directly access the field using getattr to see the exact type
            email = getattr(doc, field, None)
            
            # Log the type and value of the email
            frappe.log_error(f"Email type: {type(email)}, Email value: {email}")
            
            # If it's None, try using doc.get()
            if email is None:
                email = doc.get(field)
                frappe.log_error(f"After doc.get(), Email type: {type(email)}, Email value: {email}")
            
            # Handle different possible types
            if isinstance(email, str):
                return email.lower()
            elif isinstance(email, dict):
                # Try to extract email from dictionary
                extracted_email = email.get('name') or email.get('email') or email.get('value')
                return extracted_email.lower() if isinstance(extracted_email, str) else None
            
            return None
        except Exception as e:
            frappe.log_error(f"Comprehensive error retrieving email for {field}: {str(e)}")
            return None

    # Function to check if user is part of any other active projects
    def is_user_in_active_projects(email):
        if not email:
            return False
        
        try:
            # Construct filters manually with complete filter format
            filters = [
                ['AGK_Projects', 'status', '=', 'Active'],
                ['AGK_Projects', 'primary_approver', '=', email]
            ]
            
            # Add an OR condition for proxy_approver
            proxy_filters = [
                ['AGK_Projects', 'status', '=', 'Active'],
                ['AGK_Projects', 'proxy_approver', '=', email]
            ]
            
            # Use or_filters to handle multiple conditions
            active_projects = frappe.get_all(
                'AGK_Projects', 
                filters=filters,
                or_filters=proxy_filters
            )
            
            return len(active_projects) > 1  # More than current project
        except Exception as e:
            error_msg = f"Error checking active projects for {email}: {str(e)}"
            frappe.log_error(error_msg[:140])  # Truncate to 140 characters
            return False

    # Function to manage role for a specific user
    def manage_project_lead_role(email, role, old_email=None):
        if not email:
            # Remove role if email is blank and user is not in any other active projects
            if old_email and not is_user_in_active_projects(old_email):
                remove_role(old_email, role)
            return

        # If project is not Active, remove roles
        if doc.status != 'Active':
            if email:
                remove_role(email, role)
            return

        # Add role if not already assigned
        if not frappe.db.exists('Has Role', {'parent': email, 'role': role}):
            add_role(email, role)

        # Remove old role if email changed and old user is not in any other active projects
        if old_email and old_email != email and not is_user_in_active_projects(old_email):
            remove_role(old_email, role)

    # Manage Primary Project Lead Role
    manage_project_lead_role(
        safe_get_email(doc, 'primary_approver'), 
        'Project Lead', 
        safe_get_email(old_doc, 'primary_approver') if old_doc else None
    )

    # Manage Proxy Project Lead Role
    manage_project_lead_role(
        safe_get_email(doc, 'proxy_approver'), 
        'Proxy Project Lead', 
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
