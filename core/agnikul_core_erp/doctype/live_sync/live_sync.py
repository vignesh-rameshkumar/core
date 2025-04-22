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
                target_doc.set(target_field, source_value)
                
            # Process child tables if configured
            self._process_child_tables(doc, target_doc, is_forward)
                
            # Save target document
            target_doc.save(ignore_permissions=True)
            
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
                new_doc.set(target_field, source_value)
                
            # Process child tables if configured
            self._process_child_tables(doc, new_doc, is_forward)
                
            # Insert new document
            new_doc.insert(ignore_permissions=True)
            
            self._log_sync(doc, new_doc, "insert", is_forward)
            
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
            # Get table and field information based on direction
            if is_forward:
                source_table = mapping.get("source_table")
                source_field = mapping.get("source_field")
                target_table = mapping.get("target_table")
                target_field = mapping.get("target_field")
            else:
                source_table = mapping.get("target_table")
                source_field = mapping.get("target_field")
                target_table = mapping.get("source_table")
                target_field = mapping.get("source_field")
                
            # Skip if fields are not defined
            if not all([source_table, source_field, target_table, target_field]):
                continue
                
            # Get source rows
            source_rows = source_doc.get(source_table, [])
            
            # Create new target rows
            target_rows = []
            for source_row in source_rows:
                target_row = {"doctype": frappe.get_meta(target_doc.doctype).get_field(target_table).options}
                target_row[target_field] = source_row.get(source_field)
                target_rows.append(target_row)
                
            # Set target rows
            target_doc.set(target_table, target_rows)
            
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
            
            # Set up field mappings
            field_mappings = []
            config_mappings = self.config.get("direct_fields", {})
            
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
            
    @frappe.whitelist()
    def trigger_sync_for_document(self, doctype, docname):
        """Manually trigger sync for a document"""
        try:
            # Get document
            doc = frappe.get_doc(doctype, docname)
            
            # Determine direction
            is_forward = (doctype == self.source_doctype)
            
            # Process sync
            self.sync_document(doc, "on_update", is_forward)
            
            return {
                "success": True,
                "message": f"Sync triggered for {doctype} {docname}"
            }
        except Exception as e:
            frappe.log_error(f"Manual sync error: {str(e)}\n{traceback.format_exc()}", "LiveSync Manual Error")
            return {"success": False, "message": str(e)}