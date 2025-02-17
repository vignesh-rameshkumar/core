from frappe import _, throw  # Import for translations and error handling
from frappe.utils.response import json_handler  # Import for JSON responses
import frappe  # Main Frappe framework import
import json  # For JSON handling

@frappe.whitelist()
def approvers(code):
    try:
        # Fetch the parent document where the code exists in the child table
        project = frappe.get_all(
            "AGK_Projects",
            filters={"status": "Active"},
            fields=["name", "primary_approver", "proxy_approver"],
            or_filters=[
                ["Project Detail", "code", "=", code]
            ]
        )

        # If no project is found, raise an error
        if not project:
            throw(_("No project found with the provided code."))

        # Return the approvers
        return {
            "primary_approver": project[0].get("primary_approver"),
            "proxy_approver": project[0].get("proxy_approver")
        }
    except Exception as e:
        # Handle exceptions and return an error response
        throw(_("An error occurred while fetching approvers: {0}").format(str(e)))

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
            fields=["name", "primary_approver"]
        )
        active_project_names = [project["name"] for project in active_projects]

        # Fetch child details only for active parent projects with limit and offset
        details = [
            {
                "name1": detail["name1"],
                "code": detail["code"],
                "approver": next(
                    (project["primary_approver"] for project in active_projects if project["name"] == detail["parent"]),
                    None
                )
            }
            for detail in frappe.get_all(
                "Project Detail",
                filters={"parent": ["in", active_project_names]},
                fields=["name1", "code", "parent"],
                start=start,
                limit=limit
            )
        ]

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
