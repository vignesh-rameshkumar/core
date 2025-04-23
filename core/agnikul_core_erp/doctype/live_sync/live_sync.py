import frappe
import json
from frappe.model.document import Document
from frappe.utils import now_datetime
import traceback

class LiveSync(Document):
    def __init__(self, *args, **kwargs):
        super(LiveSync, self).__init__(*args, **kwargs)
        
        # Parse config if needed
        if isinstance(self.config, str):
            try:
                self.config = json.loads(self.config)
            except:
                self.config = {}
        elif not self.config:
            self.config = {}
            
    def validate(self):
        self.validate_config()
        self.check_bidirectional_conflicts()
        
    def validate_config(self):
        """Ensure configuration is valid"""
        # Check that required fields exist
        if not self.source_doctype:
            frappe.throw("Source DocType is required")
            
        if not self.target_doctype:
            frappe.throw("Target DocType is required")
            
        # Make sure config has proper structure
        if not isinstance(self.config, dict):
            self.config = {}
            
        if "direct_fields" not in self.config:
            self.config["direct_fields"] = {}
            
        # Ensure we have at least one field mapping
        if not self.config["direct_fields"]:
            frappe.throw("At least one field mapping is required in direct_fields")
            
        # Check field existence in doctypes
        for source_field, target_field in self.config["direct_fields"].items():
            if not frappe.get_meta(self.source_doctype).has_field(source_field):
                frappe.throw(f"Source field '{source_field}' does not exist in {self.source_doctype}")
                
            if not frappe.get_meta(self.target_doctype).has_field(target_field):
                frappe.throw(f"Target field '{target_field}' does not exist in {self.target_doctype}")
                
    def check_bidirectional_conflicts(self):
        """Prevent infinite loops with bidirectional syncs"""
        if not self.bidirectional:
            return
            
        # Skip for new documents
        if self.is_new():
            return
            
        # Check for circular reference
        existing_syncs = frappe.get_all(
            "Live Sync",
            filters={
                "source_doctype": self.target_doctype,
                "target_doctype": self.source_doctype,
                "bidirectional": 1,
                "enabled": 1,
                "name": ["!=", self.name]
            },
            fields=["name"]
        )
        
        if existing_syncs:
            frappe.throw(f"Circular reference detected with existing sync: {existing_syncs[0].name}")
            
    def on_update(self):
        """Clear cache when configuration changes"""
        self.clear_sync_cache()
        
    def clear_sync_cache(self):
        """Clear all sync cache"""
        # Clear cache for source doctype
        frappe.cache().delete_value(f"sync_configs_for_{self.source_doctype}")
        
        # Clear cache for target doctype if bidirectional
        if self.bidirectional:
            frappe.cache().delete_value(f"sync_configs_for_{self.target_doctype}")
            
    def find_matching_document(self, doc, is_forward=True):
        """Find matching document in target doctype"""
        if is_forward:
            source_doc = doc
            source_doctype = self.source_doctype
            target_doctype = self.target_doctype
        else:
            source_doc = doc
            source_doctype = self.target_doctype
            target_doctype = self.source_doctype
        
        # Get the first field mapping to use as identifier
        field_mappings = self.config.get("direct_fields", {})
        if not field_mappings:
            return None
            
        # Use the first field mapping as identifier
        source_field, target_field = next(iter(field_mappings.items()))
        
        if not is_forward:
            # Swap fields for backward direction
            source_field, target_field = target_field, source_field
            
        # Get value from source doc
        source_value = source_doc.get(source_field)
        if not source_value:
            return None
            
        # Find matching document
        try:
            target_docs = frappe.get_all(
                target_doctype, 
                filters={target_field: source_value},
                fields=["name"]
            )
            
            if target_docs:
                return frappe.get_doc(target_doctype, target_docs[0].name)
        except Exception as e:
            frappe.log_error(f"Error finding matching document: {str(e)}", "LiveSync Error")
            
        return None
        
    def sync_document(self, doc, event, is_forward=True):
        """Sync document based on event type"""
        # Skip if document is already being synced
        if hasattr(doc, "_syncing") and doc._syncing:
            return
            
        # Skip if sync is disabled
        if not self.enabled:
            return
            
        # For bidirectional check, skip if not bidirectional and not forward direction
        if not is_forward and not self.bidirectional:
            return
            
        # Set up source and target doctypes based on direction
        if is_forward:
            source_doctype = self.source_doctype
            target_doctype = self.target_doctype
        else:
            source_doctype = self.target_doctype
            target_doctype = self.source_doctype
            
        # Make sure doc is from the correct doctype
        if doc.doctype != source_doctype:
            return
                
        # Debug log
        frappe.log_error(
            f"Syncing {doc.doctype} {doc.name}, child tables: {[table for table in doc.__dict__ if isinstance(doc.get(table), list) and len(doc.get(table)) > 0]}",
            "LiveSync Debug"
        )
        
        # Mark document as being synced to prevent loops
        doc._syncing = True
        
        try:
            if event in ["after_insert", "on_update", "after_update"]:
                # Handle creation or update
                self._handle_insert_or_update(doc, event, is_forward)
            elif event in ["on_trash", "after_delete"]:
                # Handle deletion
                self._handle_delete(doc, is_forward)
        except Exception as e:
            frappe.log_error(
                f"Sync error for {doc.doctype} {doc.name}: {str(e)}\n{traceback.format_exc()}",
                "LiveSync Error"
            )
        finally:
            # Clear syncing flag
            doc._syncing = False
            
    def _handle_insert_or_update(self, doc, event, is_forward=True):
        """Handle document insertion or update"""
        # Execute before_sync hook if defined
        if self.config.get("hooks", {}).get("before_sync"):
            self._execute_hook(self.config["hooks"]["before_sync"], doc, is_forward)
        
        # Find matching document
        target_doc = self.find_matching_document(doc, is_forward)
        
        # Set up source and target field mappings
        field_mappings = self.config.get("direct_fields", {})
        if not is_forward:
            # Reverse mappings for backward direction
            field_mappings = {v: k for k, v in field_mappings.items()}
            
        if target_doc:
            # Update existing document
            target_doc._syncing = True
            
            # Apply field mappings
            for source_field, target_field in field_mappings.items():
                source_value = doc.get(source_field)
                # Apply transformation if defined
                source_value = self._apply_transform(source_field, source_value, doc)
                target_doc.set(target_field, source_value)
                
            # Process child tables if configured
            self._process_child_tables(doc, target_doc, is_forward)
                
            # Save target document
            target_doc.save(ignore_permissions=True)
            
            # Execute after_sync hook if defined
            if self.config.get("hooks", {}).get("after_sync"):
                self._execute_hook(self.config["hooks"]["after_sync"], doc, is_forward, target_doc)
            
            self._log_sync(doc, target_doc, "update", is_forward)
        else:
            # Create new document
            if is_forward:
                target_doctype = self.target_doctype
            else:
                target_doctype = self.source_doctype
                
            new_doc = frappe.new_doc(target_doctype)
            new_doc._syncing = True
            
            # Apply field mappings
            for source_field, target_field in field_mappings.items():
                source_value = doc.get(source_field)
                # Apply transformation if defined
                source_value = self._apply_transform(source_field, source_value, doc)
                new_doc.set(target_field, source_value)
                
            # Process child tables if configured
            self._process_child_tables(doc, new_doc, is_forward)
                
            # Insert new document
            new_doc.insert(ignore_permissions=True)
            
            # Execute after_sync hook if defined
            if self.config.get("hooks", {}).get("after_sync"):
                self._execute_hook(self.config["hooks"]["after_sync"], doc, is_forward, new_doc)
            
            self._log_sync(doc, new_doc, "insert", is_forward)

    def _execute_hook(self, hook_name, source_doc, is_forward, target_doc=None):
        """Execute a custom hook function"""
        try:
            if "." in hook_name:
                # Module and function specified (e.g., "mymodule.myfunction")
                module_name, function_name = hook_name.rsplit(".", 1)
                module = frappe.get_module(module_name)
                if hasattr(module, function_name):
                    hook_function = getattr(module, function_name)
                    if target_doc:
                        hook_function(source_doc, target_doc, is_forward, self)
                    else:
                        hook_function(source_doc, is_forward, self)
            else:
                # Global function
                if frappe.get_attr(hook_name):
                    hook_function = frappe.get_attr(hook_name)
                    if target_doc:
                        hook_function(source_doc, target_doc, is_forward, self)
                    else:
                        hook_function(source_doc, is_forward, self)
        except Exception as e:
            frappe.log_error(
                f"Error executing hook {hook_name}: {str(e)}\n{frappe.get_traceback()}",
                "LiveSync Hook Error"
            )

    def _apply_transform(self, field_name, value, doc):
        """Apply transformation to a field value"""
        transform_config = self.config.get("transform", {})
        
        if field_name in transform_config:
            transform_name = transform_config[field_name]
            
            try:
                if "." in transform_name:
                    # Module and function specified (e.g., "mymodule.myfunction")
                    module_name, function_name = transform_name.rsplit(".", 1)
                    module = frappe.get_module(module_name)
                    if hasattr(module, function_name):
                        transform_function = getattr(module, function_name)
                        return transform_function(value, doc)
                else:
                    # Global function
                    if frappe.get_attr(transform_name):
                        transform_function = frappe.get_attr(transform_name)
                        return transform_function(value, doc)
            except Exception as e:
                frappe.log_error(
                    f"Error applying transform {transform_name} to {field_name}: {str(e)}\n{frappe.get_traceback()}",
                    "LiveSync Transform Error"
                )
                
        return value
                
    def _handle_delete(self, doc, is_forward=True):
        """Handle document deletion"""
        # Get delete action from configuration
        delete_action = getattr(self, "on_delete_action", "None")
        if delete_action == "None":
            return
            
        # Find matching document
        target_doc = self.find_matching_document(doc, is_forward)
        if not target_doc:
            return
            
        target_doc._syncing = True
        
        if delete_action == "Delete":
            # Delete target document
            target_doc.delete(ignore_permissions=True)
            self._log_sync(doc, target_doc, "delete", is_forward)
        elif delete_action == "Archive":
            # Set status to archived
            if hasattr(target_doc, "status"):
                target_doc.status = "Archived"
                target_doc.save(ignore_permissions=True)
                self._log_sync(doc, target_doc, "archive", is_forward)
        elif delete_action == "Set Field" and hasattr(self, "on_delete_field"):
            # Set specified field to mark as deleted
            field_name = self.on_delete_field
            if hasattr(target_doc, field_name):
                target_doc.set(field_name, 1)
                target_doc.save(ignore_permissions=True)
                self._log_sync(doc, target_doc, "set_field", is_forward)
                
    def _process_child_tables(self, source_doc, target_doc, is_forward=True):
        """Process child table mappings"""
        child_mappings = self.config.get("child_mappings", [])
        if not child_mappings:
            return
            
        for mapping in child_mappings:
            # Get table information based on direction
            if is_forward:
                source_table = mapping.get("source_table")
                target_table = mapping.get("target_table")
                fields = mapping.get("fields", {})
            else:
                source_table = mapping.get("target_table") 
                target_table = mapping.get("source_table")
                # Invert the field mappings
                fields = {v: k for k, v in mapping.get("fields", {}).items()}
                
            # Skip if required fields are missing
            if not source_table or not target_table or not fields:
                frappe.log_error(
                    f"Missing required fields in child mapping: {mapping}",
                    "LiveSync Error"
                )
                continue
                
            # Check if source table exists in source document
            if not hasattr(source_doc, source_table):
                frappe.log_error(
                    f"Source document {source_doc.doctype} {source_doc.name} doesn't have child table '{source_table}'",
                    "LiveSync Error"
                )
                continue
                
            # Get source rows
            source_rows = source_doc.get(source_table, [])
            
            # Get target child table doctype
            try:
                child_doctype = frappe.get_meta(target_doc.doctype).get_field(target_table).options
            except Exception as e:
                frappe.log_error(
                    f"Error getting child table doctype: {str(e)}",
                    "LiveSync Error"
                )
                continue
                
            # Create target rows
            target_rows = []
            for source_row in source_rows:
                # Create a new row
                row_dict = {"doctype": child_doctype}
                
                # Map fields
                for src_field, tgt_field in fields.items():
                    if hasattr(source_row, src_field):
                        row_dict[tgt_field] = source_row.get(src_field)
                    else:
                        # Try dict access if attribute access fails
                        try:
                            row_dict[tgt_field] = source_row[src_field]
                        except (KeyError, TypeError):
                            frappe.log_error(
                                f"Source field {src_field} not found in row of {source_table}",
                                "LiveSync Error"
                            )
                
                # Add the row
                target_rows.append(row_dict)
            
            # Remove all existing rows and add new ones
            target_doc.set(target_table, [])
            
            # Add the new rows
            for row in target_rows:
                target_doc.append(target_table, row)
            
            frappe.log_error(
                f"Processed {len(source_rows)} rows from {source_table} to {target_table}",
                "LiveSync Debug"
            )
                
    def _update_child_rows(self, source_rows, target_doc, target_table, target_doctype, 
                        field_mappings, key_field, source_key_field):
        """Update child rows based on key field"""
        # Get existing target rows
        existing_rows = {row.get(key_field): row for row in target_doc.get(target_table, [])}
        new_rows = []
        
        for source_row in source_rows:
            source_key_value = source_row.get(source_key_field)
            if not source_key_value:
                continue
                
            if source_key_value in existing_rows:
                # Update existing row
                target_row = existing_rows[source_key_value]
                for source_field, target_field in field_mappings.items():
                    if hasattr(source_row, source_field):
                        target_row.set(target_field, source_row.get(source_field))
                new_rows.append(target_row)
            else:
                # Create new row
                target_row = frappe.new_doc(target_doctype)
                target_row.doctype = target_doctype
                for source_field, target_field in field_mappings.items():
                    if hasattr(source_row, source_field):
                        target_row.set(target_field, source_row.get(source_field))
                new_rows.append(target_row)
                
        # Update the target document with the updated/new rows
        target_doc.set(target_table, new_rows)
            
    def _replace_child_rows(self, source_rows, target_doc, target_table, target_doctype, field_mappings):
        """Replace all child rows"""
        new_rows = []
        
        for source_row in source_rows:
            target_row = frappe.new_doc(target_doctype)
            target_row.doctype = target_doctype
            
            for source_field, target_field in field_mappings.items():
                if hasattr(source_row, source_field):
                    target_row.set(target_field, source_row.get(source_field))
                    
            new_rows.append(target_row)
            
        # Replace all rows in the target document
        target_doc.set(target_table, new_rows)
            
    def _log_sync(self, source_doc, target_doc, action, is_forward):
        """Log synchronization action"""
        if not getattr(self, "enable_logging", True):
            return
            
        direction = "Forward" if is_forward else "Backward"
        
        frappe.get_doc({
            "doctype": "Sync Log",
            "sync_configuration": self.name,
            "timestamp": now_datetime(),
            "source_doctype": source_doc.doctype,
            "source_doc": source_doc.name,
            "target_doctype": target_doc.doctype,
            "target_doc": target_doc.name,
            "status": "Success",
            "direction": direction,
            "event": action.capitalize(),
            "user": frappe.session.user
        }).insert(ignore_permissions=True)
        
    @frappe.whitelist()
    def test_sync(self, source_doctype=None, source_name=None):
        """Test sync configuration with a sample document"""
        if not source_doctype:
            source_doctype = self.source_doctype
            
        if not source_name:
            # Get a random document
            docs = frappe.get_all(source_doctype, limit=1)
            if not docs:
                return {"success": False, "message": f"No documents found in {source_doctype}"}
            source_name = docs[0].name
            
        try:
            # Get source document
            source_doc = frappe.get_doc(source_doctype, source_name)
            
            # Check if document matches any target
            is_forward = (source_doctype == self.source_doctype)
            target_doc = self.find_matching_document(source_doc, is_forward)
            
            # Set up direct field mappings
            field_mappings = []
            config_mappings = self.config.get("direct_fields", {})
            
            if not is_forward:
                # Reverse mappings for backward direction
                config_mappings = {v: k for k, v in config_mappings.items()}
                
            for source_field, target_field in config_mappings.items():
                # Get original value
                source_value = source_doc.get(source_field)
                
                # Check if a transformation would be applied
                transformed_value = source_value
                transform_info = ""
                
                if self.config.get("transform", {}).get(source_field):
                    transform_function = self.config["transform"][source_field]
                    transform_info = f"Would apply: {transform_function}"
                
                field_mappings.append({
                    "source_field": source_field,
                    "target_field": target_field,
                    "value": source_value,
                    "transform": transform_info
                })
            
            # Set up child table mappings
            child_mappings = []
            config_child_mappings = self.config.get("child_mappings", [])
            
            for mapping in config_child_mappings:
                if is_forward:
                    source_table = mapping.get("source_table")
                    target_table = mapping.get("target_table")
                    fields = mapping.get("fields", {})
                else:
                    # Reverse for backward direction
                    source_table = mapping.get("target_table")
                    target_table = mapping.get("source_table")
                    # Invert the field mappings
                    fields = {v: k for k, v in mapping.get("fields", {}).items()}
                
                # Get source rows
                source_rows = source_doc.get(source_table, [])
                row_count = len(source_rows)
                
                # Sample data from first row
                sample_data = {}
                if row_count > 0:
                    for src_field, tgt_field in fields.items():
                        if hasattr(source_rows[0], src_field):
                            sample_data[src_field] = source_rows[0].get(src_field)
                
                child_mappings.append({
                    "source_table": source_table,
                    "target_table": target_table,
                    "row_count": row_count,
                    "fields": fields,
                    "sample_data": sample_data
                })
            
            # Check for hooks
            hooks_info = {}
            if self.config.get("hooks", {}).get("before_sync"):
                hooks_info["before_sync"] = self.config["hooks"]["before_sync"]
            if self.config.get("hooks", {}).get("after_sync"):
                hooks_info["after_sync"] = self.config["hooks"]["after_sync"]
            
            # Return comprehensive test results
            return {
                "success": True,
                "source_doc": source_name,
                "source_doctype": source_doctype,
                "target_exists": bool(target_doc),
                "target_doc": target_doc.name if target_doc else None,
                "target_doctype": self.target_doctype if is_forward else self.source_doctype,
                "direction": "Forward" if is_forward else "Backward",
                "field_mappings": field_mappings,
                "child_mappings": child_mappings,
                "hooks": hooks_info
            }
                    
        except Exception as e:
            frappe.log_error(f"Test sync error: {str(e)}\n{traceback.format_exc()}", "LiveSync Test Error")
            return {"success": False, "message": str(e)}
            
    @frappe.whitelist()
    def trigger_sync_for_document(self, doctype, docname):
        """Manually trigger sync for a document"""
        try:
            # Load the document with full details including child tables
            doc = frappe.get_doc(doctype, docname)
            
            # Log initial state
            frappe.log_error(
                f"Triggering sync for {doctype} {docname}, child tables: {[table for table in doc.__dict__ if isinstance(doc.get(table), list) and len(doc.get(table)) > 0]}",
                "LiveSync Debug"
            )
            
            # Determine direction
            is_forward = (doctype == self.source_doctype)
            
            # Process sync
            self.sync_document(doc, "on_update", is_forward)
            
            # Get target doc info for confirmation
            target_info = ""
            if is_forward:
                target_doctype = self.target_doctype
            else:
                target_doctype = self.source_doctype
                
            target_doc = self.find_matching_document(doc, is_forward)
            if target_doc:
                target_info = f" - Updated {target_doctype} {target_doc.name}"
            
            return {
                "success": True,
                "message": f"Sync triggered for {doctype} {docname}{target_info}"
            }
        except Exception as e:
            frappe.log_error(f"Manual sync error: {str(e)}\n{traceback.format_exc()}", "LiveSync Manual Error")
            return {"success": False, "message": str(e)}
        
    @frappe.whitelist()
    def trigger_bulk_sync(self, source_doctype=None, filters=None, limit=100):
        
        try:
            # Default to source doctype if not specified
            if not source_doctype:
                source_doctype = self.source_doctype
                
            # Determine sync direction
            is_forward = (source_doctype == self.source_doctype)
            
            # Parse filters if provided as string
            if isinstance(filters, str):
                filters = json.loads(filters)
            
            # Default to empty dict if no filters
            if not filters:
                filters = {}
                
            # Get documents matching filters
            docs = frappe.get_all(
                source_doctype,
                filters=filters,
                limit=limit,
                fields=["name"]
            )
            
            if not docs:
                return {
                    "success": False,
                    "message": f"No documents found matching filters in {source_doctype}"
                }
                
            # For larger sets, use a background job
            if len(docs) > 10:
                # Enqueue background job
                frappe.enqueue(
                    'core.agnikul_core_erp.doctype.live_sync.live_sync.process_bulk_sync',
                    queue='long',
                    timeout=3600,
                    sync_config=self.name,
                    source_doctype=source_doctype,
                    doc_names=[d.name for d in docs],
                    is_forward=is_forward,
                    now=False
                )
                
                return {
                    "success": True,
                    "message": f"Bulk sync of {len(docs)} documents has been queued as a background job. Check Sync Logs for results."
                }
            else:
                # Process directly for smaller sets
                results = {
                    "total": len(docs),
                    "processed": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "details": []
                }
                
                for doc in docs:
                    try:
                        # Get full document
                        source_doc = frappe.get_doc(source_doctype, doc.name)
                        
                        # Process sync
                        self.sync_document(source_doc, "on_update", is_forward)
                        
                        results["succeeded"] += 1
                        results["details"].append({
                            "name": doc.name,
                            "status": "Success"
                        })
                    except Exception as e:
                        results["failed"] += 1
                        results["details"].append({
                            "name": doc.name,
                            "status": "Failed",
                            "error": str(e)
                        })
                    
                    results["processed"] += 1
                    
                return {
                    "success": True,
                    "message": f"Processed {results['processed']} documents: {results['succeeded']} succeeded, {results['failed']} failed",
                    "results": results
                }
        except Exception as e:
            frappe.log_error(f"Bulk sync error: {str(e)}\n{traceback.format_exc()}", "LiveSync Bulk Error")
            return {"success": False, "message": str(e)}
        
@frappe.whitelist()
def run_test_sync(doctype, docname, source_doctype=None, source_name=None):
    """Bridge function to call instance method"""
    sync_doc = frappe.get_doc("Live Sync", docname)
    
    if not source_doctype:
        source_doctype = sync_doc.source_doctype
        
    if not source_name:
        # Get a random document
        docs = frappe.get_all(source_doctype, limit=1)
        if not docs:
            return {"success": False, "message": f"No documents found in {source_doctype}"}
        source_name = docs[0].name
        
    try:
        # Get source document
        source_doc = frappe.get_doc(source_doctype, source_name)
        
        # Check if document matches any target
        is_forward = (source_doctype == sync_doc.source_doctype)
        target_doc = sync_doc.find_matching_document(source_doc, is_forward)
        
        # Set up field mappings
        field_mappings = []
        config_mappings = sync_doc.config.get("direct_fields", {})
        
        if not is_forward:
            # Reverse mappings for backward direction
            config_mappings = {v: k for k, v in config_mappings.items()}
            
        for source_field, target_field in config_mappings.items():
            field_mappings.append({
                "source_field": source_field,
                "target_field": target_field,
                "value": source_doc.get(source_field)
            })
                
        # Return test results
        return {
            "success": True,
            "source_doc": source_name,
            "target_exists": bool(target_doc),
            "target_doc": target_doc.name if target_doc else None,
            "field_mappings": field_mappings
        }
                
    except Exception as e:
        frappe.log_error(f"Test sync error: {str(e)}\n{traceback.format_exc()}", "LiveSync Test Error")
        return {"success": False, "message": str(e)}
    
def process_bulk_sync(sync_config, source_doctype, doc_names, is_forward):
    """
    Process bulk sync in background
    
    Args:
        sync_config: Name of LiveSync configuration
        source_doctype: DocType to sync from
        doc_names: List of document names to sync
        is_forward: Direction of sync
    """
    try:
        # Get sync configuration
        sync = frappe.get_doc("Live Sync", sync_config)
        
        # Initialize counters
        total = len(doc_names)
        processed = 0
        succeeded = 0
        failed = 0
        
        # Process in batches of 20
        batch_size = 50
        
        for i in range(0, total, batch_size):
            batch = doc_names[i:i+batch_size]
            
            for doc_name in batch:
                try:
                    # Get full document
                    source_doc = frappe.get_doc(source_doctype, doc_name)
                    
                    # Process sync
                    sync.sync_document(source_doc, "on_update", is_forward)
                    
                    succeeded += 1
                except Exception as e:
                    failed += 1
                    frappe.log_error(
                        f"Error syncing {source_doctype} {doc_name}: {str(e)}",
                        "Bulk Sync Error"
                    )
                
                processed += 1
                
                # Update progress every 10 documents
                if processed % 10 == 0:
                    frappe.publish_progress(
                        percent=processed * 100 / total,
                        title="Bulk Sync",
                        description=f"Processed {processed} of {total} documents"
                    )
            
            # Commit after each batch
            frappe.db.commit()
        
        # Log final results
        frappe.log_error(
            f"Bulk sync completed: {processed} processed, {succeeded} succeeded, {failed} failed",
            "Bulk Sync Complete"
        )
        
    except Exception as e:
        frappe.log_error(f"Bulk sync process error: {str(e)}\n{traceback.format_exc()}", "Bulk Sync Error")