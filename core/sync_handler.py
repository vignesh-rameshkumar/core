import frappe
import json

def process_doc_event(doc, event):
    """Process document events for sync"""
    # Skip if Live Sync DocType doesn't exist (e.g., during uninstallation)
    if not frappe.db.exists('DocType', 'Live Sync'):
        return
        
    # Skip system doctypes
    if doc.doctype in ["Live Sync", "Sync Log"]:
        return
        
    # Skip documents being synced
    if hasattr(doc, "_syncing") and doc._syncing:
        return
        
    try:
        # Get sync configurations for this doctype
        configs = get_sync_configs_for_doctype(doc.doctype)
        if not configs:
            return
            
        # Process each configuration
        for config_name in configs:
            try:
                config = frappe.get_doc("Live Sync", config_name)
                
                # Determine sync direction
                is_forward = (doc.doctype == config.source_doctype)
                
                # Process sync
                config.sync_document(doc, event, is_forward)
            except Exception as e:
                frappe.log_error(f"Error in sync_handler for {doc.doctype} {doc.name}: {str(e)}", "LiveSync Handler Error")
    except Exception as e:
        frappe.log_error(f"General error in process_doc_event: {str(e)}", "LiveSync Error")
            
def get_sync_configs_for_doctype(doctype):
    """Get sync configs for a doctype with caching"""
    # Skip if Live Sync DocType doesn't exist (e.g., during uninstallation)
    if not frappe.db.exists('DocType', 'Live Sync'):
        return []
        
    # Check cache first
    cache_key = f"sync_configs_for_{doctype}"
    cached = frappe.cache().get_value(cache_key)
    
    if cached:
        return json.loads(cached)
        
    try:
        # Get configurations where doctype is source
        source_configs = frappe.get_all(
            "Live Sync",
            filters={"source_doctype": doctype, "enabled": 1},
            pluck="name"
        )
        
        # Get configurations where doctype is target and sync is bidirectional
        target_configs = frappe.get_all(
            "Live Sync",
            filters={"target_doctype": doctype, "bidirectional": 1, "enabled": 1},
            pluck="name"
        )
        
        # Combine results
        configs = list(set(source_configs + target_configs))
        
        # Cache for 5 minutes
        frappe.cache().set_value(cache_key, json.dumps(configs), expires_in_sec=300)
        
        return configs
    except Exception as e:
        frappe.log_error(f"Error getting sync configs: {str(e)}", "LiveSync Error")
        return []
    
def clear_sync_cache():
    """Clear all sync cache"""
    doctypes = frappe.get_all("DocType", pluck="name")
    for dt in doctypes:
        frappe.cache().delete_value(f"sync_configs_for_{dt}")