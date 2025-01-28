from frappe import _  # Import for translations
from frappe.utils.response import json_handler  # Import for JSON responses
import frappe  # Main Frappe framework import
import json  # For JSON handling

@frappe.whitelist()
def list(limit=20, start=0):
    try:
        # Convert limit and start to integers
        limit = int(limit)
        start = int(start)

        # Fetch all active parent projects
        active_projects = frappe.get_all(
            "AGK_Projects",
            filters={"status": "Active"},
            fields=["name"]
        )
        active_project_names = [project["name"] for project in active_projects]

        # Fetch child details only for active parent projects with limit and offset
        details = frappe.get_all(
            "Project Detail",
            filters={"parent": ["in", active_project_names]},
            fields=["name1", "code"],
            start=start,
            limit=limit
        )

        # Check if there are more records
        total_count = frappe.db.count("Project Detail", {"parent": ["in", active_project_names]})
        has_more = (start + limit) < total_count

        # Return the result with pagination info
        return {
            "details": details,
            "has_more": has_more,
            "next_start": start + limit
        }
    except Exception as e:
        # Handle exceptions and return an error response
        frappe.throw(_("An error occurred while fetching project details: {0}").format(str(e)))
