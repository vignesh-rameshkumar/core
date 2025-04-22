import frappe
from frappe.utils import cint, now_datetime
import json
import traceback
import time

def process_doc_event(doc, event):
    """Main entry point for document events"""
    # Skip processing for sync log and live sync doctypes
    if doc.doctype in ["Sync Log", "Live Sync"]:
        return
        
    # Prevent infinite recursion
    if hasattr(doc, "_syncing") and doc._syncing:
        return
        
    # Get active sync configurations for this doctype
    sync_configs = get_sync_configs(doc.doctype)
    
    if not sync_configs:
        return
        
    # Map Frappe events to our simplified events
    event_map = {
        "after_insert": "Insert",
        "after_update": "Update", 
        "on_update": "Update",
        "on_submit": "Update",
        "before_cancel": "Update",
        "after_trash": "Delete",
        "on_trash": "Delete"
    }
    
    mapped_event = event_map.get(event, "Update")
    
    # Process sync for each matching configuration
    for config_name in sync_configs:
        try:
            config = frappe.get_doc("Live Sync", config_name)
            
            # Skip if disabled
            if not config.enabled:
                continue
                
            # Determine sync direction
            is_forward = (doc.doctype == config.source_doctype)
            direction = "Forward" if is_forward else "Backward"
            
            # Skip backward syncs if not bidirectional
            if not is_forward and not config.bidirectional:
                continue
                
            # Check for rate limiting
            if is_rate_limited(config.name, doc.doctype, doc.name):
                continue
                
            # Process based on event type
            if mapped_event in ["Insert", "Update"]:
                # Check if we should sync
                if config.should_sync(doc, event, is_forward):
                    # Mark as being synced
                    doc._syncing = True
                    
                    # Find target document
                    target_doc = config.find_matching_target(doc, is_forward)
                    
                    if target_doc and mapped_event == "Update":
                        # Update existing target
                        mapped_doc = config.get_mapped_doc(doc, is_forward)
                        
                        # Transfer mapped values to existing doc
                        for field, value in mapped_doc.as_dict().items():
                            if field not in ["name", "owner", "creation", "modified", "modified_by"]:
                                target_doc.set(field, value)
                                
                        # Save target document with sync flag
                        target_doc._syncing = True
                        target_doc.save(ignore_permissions=True)
                        
                        config.log(
                            doc, 
                            target_doc, 
                            "Success", 
                            direction,
                            "Update"
                        )
                    elif not target_doc:
                        # Create new target
                        target_doc = config.get_mapped_doc(doc, is_forward)
                        target_doc._syncing = True
                        target_doc.insert(ignore_permissions=True)
                        
                        config.log(
                            doc, 
                            target_doc, 
                            "Success", 
                            direction,
                            "Insert"
                        )
                else:
                    # Log skip due to conditions
                    config.log(
                        doc, 
                        None, 
                        "Skipped", 
                        direction,
                        mapped_event
                    )
            elif mapped_event == "Delete" and config.on_delete_action != "None":
                # Handle deletion based on configuration
                handle_document_deletion(config, doc, is_forward)
                
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            frappe.log_error(f"Sync error: {error_msg}\n{error_trace}", "Live Sync Error")
            
            try:
                config.log(
                    doc, 
                    None, 
                    "Error", 
                    "Forward" if is_forward else "Backward",
                    mapped_event,
                    error_type="System",
                    error_message=error_msg
                )
            except:
                # If logging fails, just continue
                pass

def handle_document_deletion(config, doc, is_forward):
    """Handle document deletion based on config"""
    # Find target document
    target_doc = config.find_matching_target(doc, is_forward)
    
    if not target_doc:
        return
        
    if config.on_delete_action == "Delete":
        # Delete target document
        target_doc._syncing = True
        target_doc.delete()
        
        config.log(
            doc, 
            target_doc, 
            "Success", 
            "Forward" if is_forward else "Backward",
            "Delete"
        )
    elif config.on_delete_action == "Archive":
        # Set as archived
        target_doc._syncing = True
        
        # Try different archive field options
        if hasattr(target_doc, "archived"):
            target_doc.archived = 1
        elif hasattr(target_doc, "is_archived"):
            target_doc.is_archived = 1
        elif hasattr(target_doc, "status"):
            target_doc.status = "Archived"
        
        target_doc.save(ignore_permissions=True)
        
        config.log(
            doc, 
            target_doc, 
            "Success", 
            "Forward" if is_forward else "Backward",
            "Archive"
        )
    elif config.on_delete_action == "Set Field" and config.on_delete_field:
        # Set custom field
        field_name = config.on_delete_field
        
        if hasattr(target_doc, field_name):
            target_doc._syncing = True
            target_doc.set(field_name, 1)
            target_doc.save(ignore_permissions=True)
            
            config.log(
                doc, 
                target_doc, 
                "Success", 
                "Forward" if is_forward else "Backward",
                "Delete"
            )

def get_sync_configs(doctype):
    """Get sync configurations for doctype with caching"""
    # Try to get from cache first
    cached = frappe.cache().hget("live_sync", doctype)
    
    if cached is not None:
        return json.loads(cached)
        
    # Query database for configs
    configs = []
    
    # Check for configs where doctype is source
    source_configs = frappe.get_all(
        "Live Sync",
        filters={
            "source_doctype": doctype,
            "enabled": 1
        },
        pluck="name"
    )
    
    configs.extend(source_configs)
    
    # Check for configs where doctype is target and sync is bidirectional
    target_configs = frappe.get_all(
        "Live Sync",
        filters={
            "target_doctype": doctype,
            "bidirectional": 1,
            "enabled": 1
        },
        pluck="name"
    )
    
    configs.extend(target_configs)
    
    # Save to cache and return
    frappe.cache().hset("live_sync", doctype, json.dumps(configs))
    return configs

def is_rate_limited(config_name, doctype, docname):
    """Basic rate limiting to prevent excessive syncs"""
    cache_key = f"sync_rate_limit:{config_name}:{doctype}:{docname}"
    last_sync = frappe.cache().get_value(cache_key)
    
    if last_sync:
        # Rate limit to once per second
        if time.time() - float(last_sync) < 1:
            return True
            
    # Update timestamp and allow sync
    frappe.cache().set_value(cache_key, time.time(), expires_in_sec=10)
    return False

def clear_sync_cache():
    """Clear sync configuration cache"""
    frappe.cache().delete_key("live_sync")