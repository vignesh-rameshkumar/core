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
            # Validate source field
            self._validate_field_exists(self.source_doctype, source_field, "Source")
                
            # Validate target field
            self._validate_field_exists(self.target_doctype, target_field, "Target")
            
    def _validate_field_exists(self, doctype, field_path, field_type):
        """Validate that a field exists in the doctype, handling child tables"""
        # Check if this is a child table field
        if "." in field_path:
            # Parse the field path
            parts = field_path.split(".")
            table_part = parts[0]
            field_name = parts[1]
            
            # Remove index if present in table part
            if "[" in table_part and "]" in table_part:
                import re
                match = re.match(r'(.+)\[\d+\]', table_part)
                if match:
                    table_part = match.group(1)
                    
            # Check if the table field exists in the parent doctype
            meta = frappe.get_meta(doctype)
            table_field = meta.get_field(table_part)
            
            if not table_field:
                frappe.throw(f"{field_type} table '{table_part}' does not exist in {doctype}")
                
            if table_field.fieldtype != "Table":
                frappe.throw(f"{field_type} field '{table_part}' in {doctype} is not a Table field")
                
            # Now check if the field exists in the child table doctype
            child_doctype = table_field.options
            child_meta = frappe.get_meta(child_doctype)
            
            if not child_meta.has_field(field_name):
                frappe.throw(f"{field_type} field '{field_name}' does not exist in child table {child_doctype}")
        else:
            # Regular field check
            if not frappe.get_meta(doctype).has_field(field_path):
                frappe.throw(f"{field_type} field '{field_path}' does not exist in {doctype}")
                
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
            
    def find_matching_document(self, source_doc, is_forward=True):
        """
        Find matching document in target doctype based on identifier mapping
        
        Args:
            source_doc: The source document to find a match for
            is_forward: Direction of sync (True for source→target, False for target→source)
            
        Returns:
            The matching document or None if no match is found
        """
        # Determine source and target doctypes based on direction
        if is_forward:
            source_doctype = self.source_doctype
            target_doctype = self.target_doctype
        else:
            source_doctype = self.target_doctype
            target_doctype = self.source_doctype
        
        # Get identifier mapping or use first field mapping if not specified
        identifier_mapping = self.config.get("identifier_mapping", {})
        if not identifier_mapping:
            # If no identifier mapping is specified, use the first field mapping
            field_mappings = self.config.get("direct_fields", {})
            if field_mappings:
                first_src, first_tgt = next(iter(field_mappings.items()))
                identifier_mapping = {first_src: first_tgt}
        
        # Try each identifier mapping
        for src_field, tgt_field in identifier_mapping.items():
            # Adjust fields based on direction
            if is_forward:
                source_field, target_field = src_field, tgt_field
            else:
                source_field, target_field = tgt_field, src_field
            
            # Get source value
            source_value = None
            if "." in source_field:
                source_value = self._get_hierarchical_field_value(source_doc, source_field)
            else:
                source_value = source_doc.get(source_field)
            
            # Skip if no value
            if source_value is None:
                continue
            
            # Query for matching document
            if "." not in target_field:  # Can only query non-hierarchical fields directly
                filters = {target_field: source_value}
                target_docs = frappe.get_all(
                    target_doctype,
                    filters=filters,
                    fields=["name"],
                    limit=1
                )
                
                if target_docs:
                    return frappe.get_doc(target_doctype, target_docs[0].name)
        
        # No match found
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
        
        if target_doc:
            # Update existing document
            target_doc._syncing = True
            
            # First process hierarchical field mappings to ensure they happen before any
            # potential child table replacements
            self._process_field_mappings(doc, target_doc, is_forward)
            
            # Then process traditional child table mappings (only if there are specific child_mappings)
            if self.config.get("child_mappings"):
                self._process_child_tables(doc, target_doc, is_forward)
            
            # Save target document
            target_doc.save(ignore_permissions=True)
            
            # Execute after_sync hook if defined
            if self.config.get("hooks", {}).get("after_sync"):
                self._execute_hook(self.config["hooks"]["after_sync"], doc, is_forward, target_doc)
            
            self._log_sync(doc, target_doc, "update", is_forward)
        else:
            # Create new document
            target_doctype = self.target_doctype if is_forward else self.source_doctype
            new_doc = frappe.new_doc(target_doctype)
            new_doc._syncing = True
            
            # Process field mappings
            self._process_field_mappings(doc, new_doc, is_forward)
            
            # Process traditional child table mappings
            if self.config.get("child_mappings"):
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

    def _process_field_mappings(self, source_doc, target_doc, is_forward=True):
        """Process all field mappings with special handling for hierarchical fields"""
        # Process identifier mapping first if available
        identifier_mapping = self.config.get("identifier_mapping", {})
        if identifier_mapping:
            for src_field, tgt_field in identifier_mapping.items():
                if is_forward:
                    self._map_single_field(source_doc, target_doc, src_field, tgt_field)
                else:
                    # For reverse direction, swap source and target
                    self._map_single_field(source_doc, target_doc, tgt_field, src_field)
        
        # Process regular field mappings
        field_mappings = self.config.get("direct_fields", {})
        
        # First pass: Process regular field to regular field and child to parent mappings
        for src_field, tgt_field in field_mappings.items():
            # Skip parent to child mappings for now
            if is_forward and "." in tgt_field and "." not in src_field:
                continue
            if not is_forward and "." in src_field and "." not in tgt_field:
                continue
                
            if is_forward:
                self._map_single_field(source_doc, target_doc, src_field, tgt_field)
            else:
                # For reverse direction, swap source and target
                self._map_single_field(source_doc, target_doc, tgt_field, src_field)
        
        # Second pass: Process only parent to child mappings
        # This ensures child tables are fully populated before we try to update specific fields
        for src_field, tgt_field in field_mappings.items():
            # Only handle parent to child mappings now
            if is_forward and "." in tgt_field and "." not in src_field:
                self._map_parent_to_child_field(source_doc, target_doc, src_field, tgt_field)
            elif not is_forward and "." in src_field and "." not in tgt_field:
                self._map_parent_to_child_field(source_doc, target_doc, tgt_field, src_field)

    def _map_parent_to_child_field(self, source_doc, target_doc, parent_field, child_field_path):
        """Special handling for mapping parent field to child field using direct DB update"""
        # Get parent field value
        parent_value = source_doc.get(parent_field)
        if parent_value is None:
            return  # Skip if no value
            
        # Parse the child field path
        path_info = self._parse_table_reference(child_field_path)
        table_name = path_info["table"]
        field_name = path_info["field"]
        index = path_info["index"]
        
        # Make sure the child table exists
        meta = frappe.get_meta(target_doc.doctype)
        table_field = meta.get_field(table_name)
        if not table_field:
            frappe.log_error(f"Table field {table_name} not found in {target_doc.doctype}", "Hierarchical Field Error")
            return

        # Get the child doctype
        child_doctype = table_field.options
        
        # Get current child table
        child_table = target_doc.get(table_name, [])
        
        # Skip the normal update process and use direct DB updates instead
        # This avoids the issues with child table handling in the document model
        
        # 1. Make sure target_doc is saved first
        if target_doc.is_new():
            target_doc.insert(ignore_permissions=True)
        
        # 2. Find or create the child row
        child_row = None
        if index is not None:
            # Specific index requested
            if len(child_table) > index:
                # Row exists, use it
                child_row = child_table[index]
            else:
                # Need to create new rows up to the index
                for i in range(len(child_table), index + 1):
                    new_row = frappe.new_doc(child_doctype)
                    new_row.parent = target_doc.name
                    new_row.parenttype = target_doc.doctype
                    new_row.parentfield = table_name
                    new_row.insert(ignore_permissions=True)
                    
                    if i == index:
                        child_row = new_row
        else:
            # No index, use first row or create one
            if child_table:
                child_row = child_table[0]
            else:
                # Create first row
                child_row = frappe.new_doc(child_doctype)
                child_row.parent = target_doc.name
                child_row.parenttype = target_doc.doctype
                child_row.parentfield = table_name
                child_row.insert(ignore_permissions=True)
        
        # 3. Now update just the specific field using frappe.db.set_value
        if child_row and child_row.name:
            frappe.db.set_value(child_doctype, child_row.name, field_name, parent_value)
            frappe.log_error(
                f"Direct DB update: {child_doctype} {child_row.name}.{field_name} = {parent_value}",
                "Parent to Child Update"
            )
            
            # 4. Refresh the target document to see the changes
            target_doc.reload()

    def _map_single_field(self, source_doc, target_doc, source_field, target_field):
        """Map a single field from source to target, handling hierarchical fields"""
        # Get source value
        source_value = None
        
        if "." in source_field:
            # This is a hierarchical field
            source_value = self._get_hierarchical_field_value(source_doc, source_field)
        else:
            # Standard field
            source_value = source_doc.get(source_field)
        
        # Only proceed if we have a non-None source value
        # This prevents clearing target fields when source is None
        if source_value is not None:
            # Set target value
            if "." in target_field:
                # This is a hierarchical field
                self._set_hierarchical_field_value(target_doc, target_field, source_value)
            else:
                # Standard field
                target_doc.set(target_field, source_value)

    def _get_hierarchical_field_value(self, doc, field_path):
        """Get value from a hierarchical field path, supporting indexes"""
        # Parse the field path
        path_info = self._parse_table_reference(field_path)
        table_name = path_info["table"]
        field_name = path_info["field"]
        index = path_info["index"]
        
        # Get the child table
        child_table = doc.get(table_name, [])
        if not child_table:
            return None
        
        # Get the row based on index
        if index is not None:
            # Use specific index
            if len(child_table) > index:
                return child_table[index].get(field_name)
            else:
                return None
        else:
            # Use first row by default
            return child_table[0].get(field_name) if child_table else None

    def _set_hierarchical_field_value(self, doc, field_path, value):
        """Set value in a hierarchical field path, supporting indexes"""
        # Parse the field path
        path_info = self._parse_table_reference(field_path)
        table_name = path_info["table"]
        field_name = path_info["field"]
        index = path_info["index"]
        
        # Make sure the table field exists in the doctype
        meta = frappe.get_meta(doc.doctype)
        table_field = meta.get_field(table_name)
        if not table_field:
            frappe.log_error(f"Table field {table_name} not found in {doc.doctype}", "Hierarchical Field Error")
            return

        # Get the child doctype
        child_doctype = table_field.options
        
        # Get existing child table (important to work with the actual table, not a copy)
        child_table = doc.get(table_name, [])
        
        # Determine which row to update or create
        if index is not None:
            # Specific index requested
            while len(child_table) <= index:
                # Create new rows until we reach the desired index
                new_row = frappe.new_doc(child_doctype)
                child_table.append(new_row)
            
            # Update the specified row
            child_table[index].set(field_name, value)
        else:
            # No index specified, use first row or create one
            if not child_table:
                # Create first row if table is empty
                new_row = frappe.new_doc(child_doctype)
                new_row.set(field_name, value)
                child_table.append(new_row)
            else:
                # Update existing first row
                child_table[0].set(field_name, value)
        
        # Important: Don't use set() for the entire table as it can cause issues
        # Instead, make sure the internal reference is updated correctly
        doc.set(table_name, child_table)
        
        # Log for debugging
        frappe.log_error(
            f"Updated {doc.doctype} {doc.name}: Set {field_path} to {value}",
            "Hierarchical Field Update"
        )

    def _parse_table_reference(self, field_path):
        """Parse a field path with potential index, like "details[0].field1" or "details.field1" """
        import re
        
        # Split into table part and field part
        parts = field_path.split(".")
        if len(parts) != 2:
            frappe.log_error(f"Invalid field path: {field_path}", "Parse Error")
            return {"table": field_path, "field": "", "index": None}
        
        table_part = parts[0]
        field_part = parts[1]
        
        # Check for index notation like "details[0]"
        index_match = re.match(r'(.+)\[(\d+)\]', table_part)
        if index_match:
            table_name = index_match.group(1)
            index = int(index_match.group(2))
        else:
            table_name = table_part
            index = None
        
        return {
            "table": table_name,
            "field": field_part,
            "index": index
        }
                        
    def _process_hierarchical_field_mapping(self, source_doc, target_doc, source_field, target_field):
        """Process field mappings that involve parent-child relationships"""
        # Parse source field path
        source_is_child = "." in source_field
        target_is_child = "." in target_field
        
        # Get source value
        source_value = None
        if source_is_child:
            source_value = self._get_child_field_value(source_doc, source_field)
        else:
            # Direct parent field
            source_value = source_doc.get(source_field)
        
        # Skip if no source value
        if source_value is None:
            return
            
        # Set target value
        if target_is_child:
            self._set_child_field_value(target_doc, target_field, source_value)
        else:
            # Direct parent field
            target_doc.set(target_field, source_value)
            
    def _parse_field_path(self, field_path):
        """Parse a field path into table, index, and field components"""
        # Check if field has an index specified
        index = None
        if "[" in field_path and "]" in field_path:
            # Extract index from something like "table_name[2].field_name"
            table_part, field_part = field_path.split(".")
            
            # Extract index from table part
            import re
            match = re.match(r'(.+)\[(\d+)\]', table_part)
            if match:
                table_name = match.group(1)
                index = int(match.group(2))
            else:
                table_name = table_part
        else:
            # No index specified
            table_name, field_name = field_path.split(".")
            
        return {
            "table_name": table_name,
            "field_name": field_name,
            "index": index
        }
        
    def _get_child_field_value(self, doc, field_path):
        """Get value from a child table field"""
        # Parse the field path
        path_info = self._parse_field_path(field_path)
        
        # Get child table
        child_table = doc.get(path_info["table_name"], [])
        if not child_table:
            return None
        
        # Check if key field is specified for this child table
        key_field = None
        for mapping in self.config.get("child_mappings", []):
            if mapping.get("source_table") == path_info["table_name"]:
                key_field = mapping.get("key_field")
                break
        
        # Get the appropriate row
        child_row = None
        if path_info["index"] is not None:
            # Use index if specified
            if len(child_table) > path_info["index"]:
                child_row = child_table[path_info["index"]]
            else:
                # Index doesn't exist
                return None
        elif key_field:
            # Try to find row by key field
            # This would need additional logic to match by key
            # For now we'll just use the first row
            child_row = child_table[0] if child_table else None
        else:
            # Default to first row
            child_row = child_table[0] if child_table else None
        
        # Get the field value from the row
        if child_row:
            return child_row.get(path_info["field_name"])
        
        return None
        
    def _set_child_field_value(self, doc, field_path, value):
        """Set value in a child table field"""
        # Parse the field path
        path_info = self._parse_field_path(field_path)
        
        # Get or create child table
        child_table = doc.get(path_info["table_name"], [])
        
        # Check if we can set an existing row or need to create one
        if path_info["index"] is not None:
            # Specific index was requested
            while len(child_table) <= path_info["index"]:
                # Create enough rows to reach the index
                child_doctype = frappe.get_meta(doc.doctype).get_field(path_info["table_name"]).options
                child_table.append(frappe.new_doc(child_doctype))
            
            # Set the value in the specified row
            child_table[path_info["index"]].set(path_info["field_name"], value)
        else:
            # No index specified, use first row or create one
            if not child_table:
                # Create first row if table is empty
                child_doctype = frappe.get_meta(doc.doctype).get_field(path_info["table_name"]).options
                child_row = frappe.new_doc(child_doctype)
                child_row.set(path_info["field_name"], value)
                child_table.append(child_row)
            else:
                # Use first existing row
                child_table[0].set(path_info["field_name"], value)
        
        # Update the table in the document
        doc.set(path_info["table_name"], child_table)
        
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