from frappe import _, throw
from frappe.utils.response import json_handler
import frappe
import json

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
def list(limit=20, start=0, query=None):
    try:
        # Convert pagination parameters to integers
        limit = int(limit)
        start = int(start)

        results = {
            "details": [],
            "has_more": False,
            "next_start": start
        }

        params = {
            "limit": limit,
            "start": start
        }

        # Base SQL with JOIN for active projects and their details
        base_sql = """
            FROM `tabAGK_Projects` p
            INNER JOIN `tabProject Detail` pd ON pd.parent = p.name
            WHERE p.status = 'Active'
        """

        # If search query is provided, include filters
        if query:
            query_param = f"%{query}%"
            base_sql += """
                AND (
                    p.project_name LIKE %(query)s
                    OR p.indicator LIKE %(query)s
                    OR pd.name1 LIKE %(query)s
                    OR pd.code LIKE %(query)s
                )
            """
            params["query"] = query_param

        # Fetch paginated results
        details = frappe.db.sql(f"""
            SELECT pd.name1, pd.code, p.primary_approver as approver
            {base_sql}
            ORDER BY pd.name1
            LIMIT %(limit)s OFFSET %(start)s
        """, params, as_dict=1)

        # Count total matching rows
        count_result = frappe.db.sql(f"""
            SELECT COUNT(*) as total
            {base_sql}
        """, params, as_dict=1)
        total_count = count_result[0]["total"]

        # Set response
        results["details"] = details
        results["has_more"] = (start + limit) < total_count
        results["next_start"] = start + limit

        return results

    except Exception as e:
        frappe.throw(_("An error occurred while fetching project details: {0}").format(str(e)))

