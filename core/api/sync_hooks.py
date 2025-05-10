import frappe
from datetime import datetime
import json
from frappe.utils import cint, get_datetime_str


######### Sync Name Hooks #########

def set_name(source_doc, target_doc, is_forward, sync_config):  
    """
    Sets the name of the target document without inserting it.
    """
    target_doctype = sync_config.target_doctype if is_forward else sync_config.source_doctype
    source_name = source_doc.name

    # If the target record already exists by name, load and return it
    if frappe.db.exists(target_doctype, source_name):
        return frappe.get_doc(target_doctype, source_name)

    # Create a new document with the correct name
    new_doc = frappe.new_doc(target_doctype)
    new_doc.name = source_name
    new_doc.__islocal = True  # Ensure Frappe treats this as new

    return new_doc


########## Helper Functions for Before Sync Hook ##########

def sync_props(source_doc, target_doc, is_forward, sync_config):
    try:
        # Log before values
        frappe.logger().debug(f"Source doc timestamps - creation: {source_doc.creation}, modified: {source_doc.modified}")
        frappe.logger().debug(f"Target doc timestamps before - creation: {getattr(target_doc, 'creation', 'None')}, modified: {getattr(target_doc, 'modified', 'None')}")
        
        # Define properties to sync
        properties_to_sync = [
            "creation",
            "modified",
            "modified_by",
            "owner"
        ]
        
        # Copy properties from source to target
        for prop in properties_to_sync:
            if hasattr(source_doc, prop) and getattr(source_doc, prop):
                setattr(target_doc, prop, getattr(source_doc, prop))
        
        # Log after values
        frappe.logger().debug(f"Target doc timestamps after - creation: {getattr(target_doc, 'creation', 'None')}, modified: {getattr(target_doc, 'modified', 'None')}")
        
        return target_doc
        
    except Exception as e:
        frappe.log_error(
            f"Error in sync_props hook: {str(e)}\n{frappe.get_traceback()}",
            "Sync Props Hook Error"
        )
        return target_doc

def sync_project(source_doc, target_doc, is_forward, sync_config):

    log_messages = []
    
    # Project Name and Department Logic for target document field
    # In forward direction, we're preparing data for the target document
    if is_forward:
        
        try:
            if hasattr(source_doc, 'project_name'):
                project_name = source_doc.project_name    

                # Target field will be requesting_for but we need to calculate it here
                # and store it somewhere on the source document
                if project_name == "General":
                    # If project is General, use department value
                    if hasattr(source_doc, 'department') and source_doc.department:
                        # Set a temporary field that will be mapped to requesting_for
                        source_doc._requesting_for_value = source_doc.department
                else:
                    # If project is not General, use project_name value
                    source_doc._requesting_for_value = project_name
                
                # Modify the direct_fields mapping dynamically to include this field
                if not sync_config.config.get("direct_fields"):
                    sync_config.config["direct_fields"] = {}
                    
                # Add or update the mapping to use our temporary field
                sync_config.config["direct_fields"]["_requesting_for_value"] = "requesting_for"
        except Exception as e:
            log_messages.append(f"Error in project logic: {str(e)}")
    
    # Log all messages together
    frappe.log_error("\n".join(log_messages), "Debug Before Sync Hook")

def apply_status_mapping(source_doc, field_name, mapping_dict, is_forward, sync_config):
    """
    Reusable function to apply a status mapping transformation.
    
    Args:
        source_doc: Source document object
        field_name: Field name to transform
        mapping_dict: Dictionary with 'forward' and 'backward' mappings
        is_forward: Direction of sync (True for forward, False for backward)
        sync_config: LiveSync configuration object
        
    Returns:
        bool: True if mapping was applied, False otherwise
    """
    # Skip if no value
    if not hasattr(source_doc, field_name) or not source_doc.get(field_name):
        return False
        
    # Get current value
    current_value = source_doc.get(field_name)
    
    # Determine direction
    direction = "forward" if is_forward else "backward"
    
    # Skip if no mapping exists
    if direction not in mapping_dict or current_value not in mapping_dict[direction]:
        return False
        
    # Get the mapped value
    new_value = mapping_dict[direction][current_value]
    
    # Set temporary field
    temp_field = f"{field_name}_mapped"
    source_doc.set(temp_field, new_value)
    
    # Initialize direct_fields if needed
    if not sync_config.config.get("direct_fields"):
        sync_config.config["direct_fields"] = {}
        
    # Map temporary field to target field
    sync_config.config["direct_fields"][temp_field] = field_name
    
    return True

def format_datetime_value(value):
    """
    Utility function to properly format datetime values to standard format.
    Can be used for any datetime field in any sync scenario.
    
    Args:
        value: Date/time value as string or datetime object
        
    Returns:
        Formatted datetime string in YYYY-MM-DD HH:MM:SS format or None
    """
    if not value:
        return None
        
    # Skip if already in correct format
    if isinstance(value, datetime):
        return get_datetime_str(value)
        
    # Handle string values
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
            
        try:
            # Try converting to datetime using standard Frappe function
            dt_value = get_datetime_str(value)
            return dt_value
        except Exception:
            # Fall back to manual parsing
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',  # 2025-04-21 14:30:00
                '%Y-%m-%d',           # 2025-04-21
                '%d-%m-%Y %H:%M:%S',  # 21-04-2025 14:30:00
                '%d-%m-%Y',           # 21-04-2025
                '%d/%m/%Y %H:%M:%S',  # 21/04/2025 14:30:00
                '%d/%m/%Y',           # 21/04/2025
                '%m/%d/%Y %H:%M:%S',  # 04/21/2025 14:30:00
                '%m/%d/%Y',           # 04/21/2025
                '%b %d, %Y %H:%M:%S',  # Apr 21, 2025 14:30:00
                '%b %d, %Y'           # Apr 21, 2025
            ]
            
            for date_format in formats_to_try:
                try:
                    dt_obj = datetime.strptime(value, date_format)
                    return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
                    
    return None

def synchronize_datetime_field(source_doc, field_name, target_field_name, sync_config):
    """
    Reusable function to format and map a datetime field.
    
    Args:
        source_doc: Source document object
        field_name: Name of the field in source document
        target_field_name: Name of the field in target document
        sync_config: LiveSync configuration object
    
    Returns:
        bool: True if field was processed, False otherwise
    """
    # Skip if no value
    if not hasattr(source_doc, field_name) or not source_doc.get(field_name):
        return False
        
    # Get current value
    date_value = source_doc.get(field_name)
    
    # Format the value
    formatted_date = format_datetime_value(date_value)
    
    # Skip if no valid date or already in correct format
    if not formatted_date or formatted_date == date_value:
        return False
        
    # Set a temporary field for the formatted date
    temp_field = f"{field_name}_formatted"
    source_doc.set(temp_field, formatted_date)
    
    # Initialize direct_fields if needed
    if not sync_config.config.get("direct_fields"):
        sync_config.config["direct_fields"] = {}
        
    # Map temporary field to target field
    sync_config.config["direct_fields"][temp_field] = target_field_name
    
    return True