# web_page.py
from __future__ import unicode_literals
import frappe
from frappe import _

no_cache = 1
no_sitemap = 1

def get_context(context):
    """Get the context for the upgrade notice page"""
    # You can add custom context here if needed
    context.title = _("Application Upgrade Notice")
    
    # Optional: Add dynamic data
    context.upgrade_message = _("This application has been upgraded to the latest version. Please access the upgraded application from the Desk page.")
    context.button_text = _("Switch to Desk")
    context.redirect_url = "/erp-desk"
    
    # Set no cache to prevent browser caching
    context.no_cache = 1
    
    # Disable website context to show minimal layout
    context.show_footer = False
    context.show_header = False
    context.hide_sidebar = True
    
    return context

# Optional: Add custom route handling
@frappe.whitelist(allow_guest=True)
def check_upgrade_status():
    """Check if user should see upgrade notice"""
    # You can add logic here to determine if the upgrade notice should be shown
    # For example, checking user preferences or session variables
    return {
        "show_notice": True,
        "message": _("Application has been successfully upgraded")
    }

# Optional: Add server-side validation
def validate_access():
    """Validate user access before showing the upgrade notice"""
    # Add custom validation logic here if needed
    pass