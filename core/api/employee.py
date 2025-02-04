import frappe

def before_validate(doc, method):
    """
    This function is triggered before validating the Employee document.
    Enables the User if the Employee status is Active and the User is disabled.
    Checks for active approver roles before potentially disabling the User.
    """
    if doc.user_id:
        # First, handle User enabling for Active status
        if doc.status == "Active":
            try:
                user = frappe.get_doc("User", doc.user_id)
                if not user.enabled:
                    # Attempt to enable the user
                    user.enabled = 1
                    user.save(ignore_permissions=True)
                    frappe.msgprint(f"User {doc.user_id} has been enabled.")
            except Exception as e:
                frappe.log_error(f"Error enabling user for Employee {doc.name}: {str(e)}")
                frappe.throw(f"Could not enable user: {str(e)}")

        # Then check for approver roles when trying to change status to non-Active
        if doc.status != "Active":
            # Check email in AGK_ERP_Products
            products = frappe.get_all('AGK_ERP_Products', 
                filters=[
                    ['primary_fl', '=', doc.user_id]
                ],
                fields=['name']
            )
            if products:
                frappe.throw(f"Cannot change Employee status. User is a primary approver in ERP Products: {', '.join([p['name'] for p in products])}")

            products = frappe.get_all('AGK_ERP_Products', 
                filters=[
                    ['proxy_fl', '=', doc.user_id]
                ],
                fields=['name']
            )
            if products:
                frappe.throw(f"Cannot change Employee status. User is a proxy approver in ERP Products: {', '.join([p['name'] for p in products])}")

            # Check in AGK_Departments
            departments = frappe.get_all('AGK_Departments', 
                filters=[
                    ['primary_approver', '=', doc.user_id]
                ],
                fields=['name']
            )
            if departments:
                frappe.throw(f"Cannot change Employee status. User is a primary approver in Departments: {', '.join([d['name'] for d in departments])}")

            departments = frappe.get_all('AGK_Departments', 
                filters=[
                    ['proxy_approver', '=', doc.user_id]
                ],
                fields=['name']
            )
            if departments:
                frappe.throw(f"Cannot change Employee status. User is a proxy approver in Departments: {', '.join([d['name'] for d in departments])}")

            # Check in AGK_Projects
            projects = frappe.get_all('AGK_Projects', 
                filters=[
                    ['primary_approver', '=', doc.user_id]
                ],
                fields=['name']
            )
            if projects:
                frappe.throw(f"Cannot change Employee status. User is a primary approver in Projects: {', '.join([p['name'] for p in projects])}")

            projects = frappe.get_all('AGK_Projects', 
                filters=[
                    ['proxy_approver', '=', doc.user_id]
                ],
                fields=['name']
            )
            if projects:
                frappe.throw(f"Cannot change Employee status. User is a proxy approver in Projects: {', '.join([p['name'] for p in projects])}")

def delete_pushnotify_user(doc, method):
    """
    Deletes the PushNotify User document if the Employee status is not Active.
    """
    if doc.status != "Active" and doc.user_id:
        try:
            # Search for the PushNotify User document by name matching user_id
            pushnotify_user = frappe.get_doc("PushNotify User", doc.user_id)
            if pushnotify_user:
                pushnotify_user.delete()
                # frappe.msgprint(f"PushNotify User {doc.user_id} has been deleted.")
        except frappe.DoesNotExistError:
            # Document not found, no action needed
            pass
        except Exception as e:
            frappe.log_error(f"Error deleting PushNotify User for Employee {doc.name}: {str(e)}")
            frappe.throw(f"Could not delete PushNotify User: {str(e)}")

def validate_user_status(doc, method):
    """
    This function is triggered during validation of the Employee document.
    Ensures User status is synchronized with Employee status.
    """
    if doc.user_id:
        try:
            # Get the current User document
            user = frappe.get_doc("User", doc.user_id)
            
            # Ensure User status matches Employee status
            user.enabled = 1 if doc.status == "Active" else 0
            user.save(ignore_permissions=True)
        
        except Exception as e:
            frappe.log_error(f"Error updating user status for Employee {doc.name}: {str(e)}")
            frappe.throw(f"Could not update user status: {str(e)}")
