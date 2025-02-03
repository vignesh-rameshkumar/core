import frappe
from frappe import _, get_doc

@frappe.whitelist()
def list():
    
    try:
        # Query the AGK_Rigs doctype
        facility = frappe.get_all(
            "AGK_Facilities",
            filters={"status": "Active"},
            fields=["facility_name", "facility_code"]
        )
        # Return the result as JSON
        return (facility)

    except Exception as e:
        frappe.throw(_("An error occurred while fetching rigs: {0}").format(str(e)))

@frappe.whitelist()
def security(doc, method):
    try:
        # Fetch the specific document from AGK_Facilities

        # Automatically generate the facility_code
        if not doc.facility_code:
            latest_code = frappe.db.sql("""
                SELECT facility_code FROM `tabAGK_Facilities`
                WHERE facility_code IS NOT NULL
                ORDER BY facility_code DESC
                LIMIT 1
            """)
            if latest_code:
                next_code = "F" + str(int(latest_code[0][0][1:]) + 1).zfill(4)
            else:
                next_code = "F0001"
            doc.facility_code = next_code
        if not doc.security_email or not doc.facility_name:
            frappe.throw(_("Missing required fields: security_email or facility_name"))

        # Check if user already exists
        user = frappe.db.exists("User", {"email": doc.security_email})
        if user:
            user_doc = frappe.get_doc("User", user)
        else:
            # Create a new user
            user_doc = frappe.get_doc({
                "doctype": "User",
                "email": doc.security_email,
                "first_name": doc.facility_name,
                "send_welcome_email": 0,
                "enabled": 1,
                "new_password": "Agn!kul@123"
            })
            user_doc.insert(ignore_permissions=True)

        # Check if the Security role exists
        role = frappe.db.exists("Role", {"role_name": "Security"})
        if not role:
            # Create the Security role
            role_doc = frappe.get_doc({
                "doctype": "Role",
                "role_name": "Security",
                "desk_access": 1
            })
            role_doc.insert(ignore_permissions=True)

        # Assign the Security role to the user
        if "Security" not in [r.role for r in user_doc.roles]:
            user_doc.append("roles", {"role": "Security"})
            user_doc.save(ignore_permissions=True)

        return _("Security setup completed successfully.")

    except Exception as e:
        frappe.throw(_("An error occurred while setting up security: {0}").format(str(e)))

@frappe.whitelist()
def validate_status(doc, method):
    try:
        # Fetch the user associated with the document's security_email
        user = frappe.db.exists("User", {"email": doc.security_email})
        if not user:
            frappe.throw(_("No user found with the email: {0}").format(doc.security_email))

        user_doc = frappe.get_doc("User", user)

        # Update the user's enabled status based on the document's status
        if doc.status == "Active":
            user_doc.enabled = 1
        elif doc.status == "Inactive":
            user_doc.enabled = 0
        else:
            frappe.throw(_("Invalid status: {0}. Allowed values are 'Active' or 'Inactive'.").format(doc.status))

        user_doc.save(ignore_permissions=True)

        return _("User status updated successfully based on document status.")

    except Exception as e:
        frappe.throw(_("An error occurred while validating status: {0}").format(str(e)))
