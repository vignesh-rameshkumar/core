import functools
import frappe
from typing import Callable, Dict, List, Any, Optional, Union
import hashlib
import json
import time

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
    project_approver = frappe.db.sql("""
        SELECT pd.name1
        FROM `tabAGK_Projects` p
        JOIN `tabProject Detail` pd ON pd.parent = p.name
        WHERE p.status = 'Active'
        AND (p.primary_approver = %s OR p.proxy_approver = %s)
    """, (id, id), as_dict=True)

    department_approver = frappe.db.sql("""
        SELECT department_name
        FROM `tabAGK_Departments`
        WHERE primary_approver = %s OR proxy_approver = %s
    """, (id, id), as_dict=True)

    result = {
        "projects": [d.name1 for d in project_approver],
        "departments": [d.department_name for d in department_approver]
    }

    return result

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