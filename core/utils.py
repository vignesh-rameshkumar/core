import functools
import frappe
from typing import Callable, Dict, List, Any, Optional, Union
import hashlib
import json
import time
from datetime import date

def paginate():
    """
    An improved decorator to add pagination functionality to Frappe API endpoints.

    Features:
    - Automatically handles limit + 1 logic
    - Transparently manages pagination for different query methods
    - Supports various Frappe query methods
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            # Extract pagination parameters
            start = kwargs.get('start', 0)
            try:
                start = int(start)
                if start < 0:
                    start = 0
            except (ValueError, TypeError):
                start = 0

            # Extract and validate limit
            limit = kwargs.get('limit', 20)
            try:
                limit = int(limit)
                if limit <= 0:
                    limit = 20
            except (ValueError, TypeError):
                limit = 20

            # Enforce maximum limit silently
            effective_limit = min(limit, 100)

            # Modify kwargs to pass to original function
            # Add one to limit for checking 'has_more'
            modified_kwargs = {**kwargs, 'start': start, 'limit': effective_limit + 1}

            # Execute the original function
            result = func(*args, **modified_kwargs)

            # Handle different return types
            items = []
            if isinstance(result, list):
                items = result
            elif isinstance(result, dict) and 'data' in result:
                items = result.get('data', [])
                # Keep the original response structure
                response = result
            else:
                items = result
                response = {'data': items}

            # Determine if there are more records
            has_more = len(items) > effective_limit

            # Slice the items to the actual requested limit
            if has_more:
                items = items[:effective_limit]
                if isinstance(result, list):
                    result = items
                else:
                    response['data'] = items

            # Calculate next_start for pagination
            next_start = start + effective_limit if has_more else None

            # Add pagination metadata
            pagination_info = {
                'has_more': has_more,
                'next_start': next_start,
                'start': start,
                'limit': effective_limit,
                'total_fetched': len(items)
            }

            # Prepare the final response
            if isinstance(result, list):
                return {
                    'data': result,
                    'pagination': pagination_info
                }
            else:
                response['pagination'] = pagination_info
                return response

        return wrapper
    return decorator


def rate_limit(time_window: int = 5):

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get current user
            user = frappe.session.user

            # Generate a unique key for this request
            # Combine user + function name + request data
            request_data = frappe.request.data if hasattr(frappe, 'request') and hasattr(frappe.request, 'data') else b''

            # Convert request data to string if it's not already
            if isinstance(request_data, bytes):
                try:
                    request_data = request_data.decode('utf-8')
                except UnicodeDecodeError:
                    # If we can't decode, use the raw bytes for hashing
                    pass

            # Create a hash of the combined data
            payload_str = f"{user}:{func.__name__}:{request_data}"
            request_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()

            # Create a cache key
            cache_key = f"rate_limit:{request_hash}"

            # Check if this request has been made recently
            last_request_time = frappe.cache().get_value(cache_key)

            current_time = time.time()

            if last_request_time:
                elapsed = current_time - float(last_request_time)

                # If the request is within the time window, block it
                if elapsed < time_window:
                    remaining_time = round(time_window - elapsed, 2)
                    frappe.throw(
                        f"Throttled. Duplicate request detected.",
                        frappe.DuplicateEntryError
                    )

            # Store the current timestamp for this request
            frappe.cache().set_value(cache_key, current_time, expires_in_sec=time_window)

            # Execute the original function
            return func(*args, **kwargs)

        return wrapper
    return decorator

@frappe.whitelist()
def approver(id):
    # Projects: combine primary + proxy
    projects = frappe.db.sql("""
        (
            SELECT pd.name1 AS name, 'primary' AS role
            FROM `tabAGK_Projects` p
            JOIN `tabProject Detail` pd ON pd.parent = p.name
            WHERE p.status = 'Active' AND p.primary_approver = %(id)s
        )
        UNION ALL
        (
            SELECT pd.name1 AS name, 'proxy' AS role
            FROM `tabAGK_Projects` p
            JOIN `tabProject Detail` pd ON pd.parent = p.name
            WHERE p.status = 'Active' AND p.proxy_approver = %(id)s
        )
    """, {"id": id}, as_dict=True)

    # Departments: combine primary + proxy
    departments = frappe.db.sql("""
        (
            SELECT department_name AS name, 'primary' AS role
            FROM `tabAGK_Departments`
            WHERE primary_approver = %(id)s
        )
        UNION ALL
        (
            SELECT department_name AS name, 'proxy' AS role
            FROM `tabAGK_Departments`
            WHERE proxy_approver = %(id)s
        )
    """, {"id": id}, as_dict=True)

    # Group by role for response formatting
    def group_by_role(data):
        grouped = {"primary": [], "proxy": []}
        for row in data:
            grouped[row.role].append(row.name)
        return grouped

    return {
        "projects": group_by_role(projects),
        "departments": group_by_role(departments)
    }

@frappe.whitelist()
@paginate()
def get_employees(dept=None, query=None, start=0, limit=20):

    filters = {"status": "Active"}

    if dept:
        filters["department"] = dept

    fields = ["employee_name", "user_id", "department"]

    if query:
        or_filters = [
            ["employee_name", "like", f"%{query}%"],
            ["user_id", "like", f"%{query}%"]
        ]
    else:
        or_filters = None

    employees = frappe.get_list(
        "Employee",
        fields=fields,
        filters=filters,
        or_filters=or_filters,
        ignore_permissions=True
    )

    return employees


@frappe.whitelist()
def get_leads(pro=None, app=None):
    approvers = {
        "pro_approvers": [],
        "app_approvers": []
    }

    # Fetch pro approvers
    pro_approvers = validate_pro_or_app("pro", pro)
    approvers["pro_approvers"] = pro_approvers

    # Fetch app approvers
    app_approvers = validate_pro_or_app("app", app)
    approvers["app_approvers"] = app_approvers

    return approvers

def validate_pro_or_app(category, value):
    primary, proxy = None, None

    if category == "pro":
        # Step 1: Check in AGK_Departments
        department = frappe.get_all("AGK_Departments",
                                    filters={"department_name": value},
                                    fields=["primary_approver", "proxy_approver"],
                                    limit=1)
        if department:
            primary, proxy = department[0]["primary_approver"], department[0]["proxy_approver"]
        else:
            # Step 2: Check in Project Detail child table
            project_detail = frappe.get_all("Project Detail",
                                            filters={"name1": value},
                                            fields=["parent"],
                                            limit=1)
            if project_detail:
                project = frappe.get_all("AGK_Projects",
                                         filters={"name": project_detail[0]["parent"]},
                                         fields=["primary_approver", "proxy_approver"],
                                         limit=1)
                if project:
                    primary, proxy = project[0]["primary_approver"], project[0]["proxy_approver"]

    elif category == "app":
        # Step 1: Check in AGK_ERP_Products
        product = frappe.get_all("AGK_ERP_Products",
                                 filters={"module_name": value},
                                 fields=["primary_fl", "proxy_fl"],
                                 limit=1)
        if product:
            primary, proxy = product[0]["primary_fl"], product[0]["proxy_fl"]

    return filter_approvers(primary, proxy)

def filter_approvers(primary, proxy):
    if not primary:
        return []

    today = date.today().strftime("%Y-%m-%d")
    leave_statuses = {"Casual Leave", "Sick Leave", "Maternity Leave", "Paternity Leave", "Festival Leave"}

    # Fetch attendance status in one query
    attendance = frappe.get_all("Attendance_Records",
                                filters={"employee_email": primary, "date": today},
                                fields=["status"],
                                limit=1)

    if attendance and attendance[0]["status"] in leave_statuses:
        return [primary, proxy] if proxy else [primary]

    return [primary]

@frappe.whitelist(allow_guest=True)
def user_roles(product=None):
    user = frappe.session.user
    roles = frappe.get_roles(user)
    if not product:
        frappe.throw(
            f"Key 'product' not found in request",
            frappe.KeyError
        )
    return roles
