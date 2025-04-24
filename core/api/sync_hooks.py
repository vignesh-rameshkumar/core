# File: your_app_name/sync_hooks.py

import frappe
import json

def store_complete_data(source_doc, is_forward, sync_config):
    """
    Before sync hook to store all source document data in the user_data JSON field
    """
    try:
        # We only want to store data when syncing from Employee to User
        if not is_forward:
            return
            
        # Skip if source doc is not Demo Employee
        if source_doc.doctype != "Demo Employee":
            return
        
        # Capture all main fields from Demo Employee
        data = {}
        for field in frappe.get_meta("Demo Employee").fields:
            if field.fieldtype not in ["Table", "Section Break", "Column Break", "Tab Break"]:
                data[field.fieldname] = source_doc.get(field.fieldname)
        
        # Capture child table data from Employee_Details
        if hasattr(source_doc, "details"):
            child_data = []
            for child_row in source_doc.get("details", []):
                row_data = {}
                # We know the fields are f1, f2, f3
                row_data["f1"] = child_row.get("f1")
                row_data["f2"] = child_row.get("f2")
                row_data["f3"] = child_row.get("f3")
                child_data.append(row_data)
            data["child_data"] = child_data
        
        # Add metadata
        data["_metadata"] = {
            "sync_timestamp": frappe.utils.now(),
            "source_doctype": "Demo Employee",
            "source_name": source_doc.name
        }
        
        # Store the data for later use in the after_sync hook
        if not hasattr(sync_config, "_temp_data"):
            sync_config._temp_data = {}
        
        sync_config._temp_data[source_doc.name] = data
        
        # Set the same name for target document
        sync_config._target_name = source_doc.name
        
        frappe.log_error(
            f"Stored complete data for {source_doc.doctype} {source_doc.name}",
            "Sync Before Hook"
        )
    
    except Exception as e:
        frappe.log_error(
            f"Error in store_complete_data hook: {str(e)}\n{frappe.get_traceback()}",
            "Sync Hook Error"
        )

def update_json_data(source_doc, target_doc, is_forward, sync_config):
    """
    After sync hook to store the captured data in the user_data field
    """
    try:
        # We only want to update the user_data field when syncing from Employee to User
        if not is_forward:
            return
            
        # Skip if target doc is not Demo User
        if target_doc.doctype != "Demo User":
            return
            
        # Get the stored data or use an empty object
        data = {}
        if hasattr(sync_config, "_temp_data") and source_doc.name in sync_config._temp_data:
            data = sync_config._temp_data[source_doc.name]
            # Clean up temp data
            del sync_config._temp_data[source_doc.name]
        
        # Always set the user_data field, even if it's just an empty object
        # This ensures the mandatory field requirement is satisfied
        target_doc.user_data = json.dumps(data, default=str)
        
        # Get the target name (should be same as source doc name)
        target_name = source_doc.name
        if hasattr(sync_config, "_target_name"):
            target_name = sync_config._target_name
        
        # If the document was just created, rename it to match the source doc
        if target_doc.name != target_name:
            try:
                # Rename the target document 
                frappe.rename_doc(target_doc.doctype, target_doc.name, target_name, force=True)
                
                # Update our reference to the renamed document
                target_doc = frappe.get_doc(target_doc.doctype, target_name)
                
                frappe.log_error(
                    f"Renamed {target_doc.doctype} from {target_doc.name} to {target_name}",
                    "Sync After Hook"
                )
            except Exception as rename_error:
                frappe.log_error(
                    f"Error renaming document: {str(rename_error)}",
                    "Sync Rename Error"
                )
        
        # Set user_data field directly to bypass validation
        frappe.db.set_value("Demo User", target_doc.name, "user_data", json.dumps(data, default=str))
        
        frappe.log_error(
            f"Updated user_data in {target_doc.doctype} {target_doc.name}",
            "Sync After Hook"
        )
    
    except Exception as e:
        frappe.log_error(
            f"Error in update_json_data hook: {str(e)}\n{frappe.get_traceback()}",
            "Sync Hook Error"
        )