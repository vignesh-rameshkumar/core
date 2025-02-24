import frappe

@frappe.whitelist()
def token():
    """Get CSRF token for the current session"""
    try:
        csrf_token = frappe.session.data.csrf_token
        if not csrf_token:
            # Generate new token if not exists
            csrf_token = frappe.generate_hash()
            frappe.session.data.csrf_token = csrf_token
            
        return {
            "csrf_token": csrf_token
        }
    except Exception as e:
        frappe.log_error("Error getting CSRF token", str(e))
        frappe.throw("Failed to get CSRF token")