# Copyright (c) 2025, Agnikul Cosmos Private Limited and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import cint, cstr, now_datetime
import traceback
from frappe.core.doctype.version.version import get_diff
import time
import ast

class LiveSync(Document):
    def validate(self):
        self.validate_circular_reference()
        
    def validate_circular_reference(self):
        """Prevent infinite loops with bidirectional syncs"""
        if not self.bidirectional:
            return
            
        # Check for circular reference with same DocTypes
        if self.source_doctype == self.target_doctype:
            frappe.throw("Source and Target DocTypes cannot be the same when bidirectional sync is enabled")
            
        # Check for circular reference with other syncs
        other_syncs = frappe.get_all(
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
        
        if other_syncs:
            sync_names = ", ".join([d.name for d in other_syncs])
            frappe.throw(f"Bidirectional loop detected with other sync configurations: {sync_names}")
            
    def on_update(self):
        """Invalidate sync cache when configuration changes"""
        frappe.cache().hdel("live_sync", self.source_doctype)
        if self.bidirectional:
            frappe.cache().hdel("live_sync", self.target_doctype)
            
    def get_mapped_doc(self, source_doc, is_forward=True):
        """Create a new target document based on mapping configuration"""
        source_doctype = self.source_doctype if is_forward else self.target_doctype
        target_doctype = self.target_doctype if is_forward else self.source_doctype
        
        # Create new target document
        target_doc = frappe.new_doc(target_doctype)
        
        # Apply field mappings
        field_mappings = self.field_mappings
        
        for mapping in field_mappings:
            source_field = mapping.source_field if is_forward else mapping.target_field
            target_field = mapping.target_field if is_forward else mapping.source_field
            
            if not hasattr(source_doc, source_field):
                self.log(
                    source_doc, 
                    None, 
                    "Skipped", 
                    "Forward" if is_forward else "Backward",
                    "Update", 
                    error_type="Validation",
                    error_message=f"Source field {source_field} does not exist in {source_doctype}"
                )
                continue
                
            value = source_doc.get(source_field)
            
            # Apply transformation if defined
            transformation = mapping.transformation
            if transformation and transformation.strip():
                try:
                    # Execute transformation in safe context
                    local_vars = {"value": value, "source_doc": source_doc, "frappe": frappe}
                    exec(transformation, None, local_vars)
                    value = local_vars.get("value")
                except Exception as e:
                    self.log(
                        source_doc, 
                        None, 
                        "Error", 
                        "Forward" if is_forward else "Backward",
                        "Update", 
                        error_type="Data",
                        error_message=f"Transformation error for {source_field}: {str(e)}"
                    )
            
            # Set value in target doc
            target_doc.set(target_field, value)
        
        # Apply child table mappings
        child_mappings = self.child_table_mappings
        
        for mapping in child_mappings:
            source_table = mapping.source_table if is_forward else mapping.target_table
            target_table = mapping.target_table if is_forward else mapping.source_table
            
            # Skip if source table doesn't exist
            if not hasattr(source_doc, source_table):
                continue
                
            source_rows = source_doc.get(source_table, [])
            target_rows = []
            
            for source_row in source_rows:
                target_row = {}
                
                # Apply field mappings for child table
                for field_mapping in mapping.field_mappings:
                    s_field = field_mapping.source_field if is_forward else field_mapping.target_field
                    t_field = field_mapping.target_field if is_forward else field_mapping.source_field
                    
                    if hasattr(source_row, s_field):
                        value = source_row.get(s_field)
                        
                        # Apply transformation if defined
                        transformation = field_mapping.transformation
                        if transformation and transformation.strip():
                            try:
                                local_vars = {"value": value, "source_row": source_row, "frappe": frappe}
                                exec(transformation, None, local_vars)
                                value = local_vars.get("value")
                            except Exception as e:
                                self.log(
                                    source_doc, 
                                    None, 
                                    "Error", 
                                    "Forward" if is_forward else "Backward",
                                    "Update", 
                                    error_type="Data",
                                    error_message=f"Child table transformation error: {str(e)}"
                                )
                        
                        target_row[t_field] = value
                
                target_rows.append(target_row)
            
            # Set child table rows in target doc
            target_doc.set(target_table, target_rows)
        
        return target_doc
        
    def should_sync(self, doc, event, is_forward=True):
        """Check if sync should be performed based on conditions"""
        # Skip if document is already being synced
        if hasattr(doc, "_syncing") and doc._syncing:
            return False
            
        # Apply conditions
        conditions = self.conditions
        
        for condition in conditions:
            field_name = condition.field
            operator = condition.operator
            expected_value = condition.value
            condition_type = condition.condition_type
            
            # Get actual value from document
            actual_value = doc.get(field_name)
            
            # Convert expected value to appropriate type
            expected_value = self.convert_value(expected_value, actual_value)
            
            # Check condition
            result = self.evaluate_condition(actual_value, operator, expected_value)
            
            if condition_type == "Skip If" and result:
                return False
                
            if condition_type == "Only If" and not result:
                return False
                
        # Check action type for the event
        if event == "after_update" or event == "after_insert":
            action = self.on_update_action
            
            if action == "Only Create" and event == "after_update":
                return False
                
            if action == "Only Update" and event == "after_insert":
                return False
        
        return True
        
    def convert_value(self, value_str, reference_value):
        """Convert string value to appropriate type based on reference"""
        if reference_value is None:
            return None
            
        try:
            # Try to convert to same type as reference value
            if isinstance(reference_value, int):
                return int(value_str)
            elif isinstance(reference_value, float):
                return float(value_str)
            elif isinstance(reference_value, bool):
                return value_str.lower() in ("1", "true", "yes", "y")
            elif isinstance(reference_value, list):
                return ast.literal_eval(value_str)
            else:
                return value_str
        except (ValueError, SyntaxError):
            # If conversion fails, return as string
            return value_str
        
    def evaluate_condition(self, actual, operator, expected):
        """Evaluate condition using operator"""
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == ">":
            return actual > expected
        elif operator == "<":
            return actual < expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "<=":
            return actual <= expected
        elif operator == "in":
            return actual in expected
        elif operator == "not in":
            return actual not in expected
        elif operator == "contains":
            return expected in actual if isinstance(actual, str) else False
        elif operator == "starts with":
            return actual.startswith(expected) if isinstance(actual, str) else False
        elif operator == "ends with":
            return actual.endswith(expected) if isinstance(actual, str) else False
        else:
            return False
            
    def find_matching_target(self, source_doc, is_forward=True):
        """Find matching target document based on field mappings"""
        source_doctype = self.source_doctype if is_forward else self.target_doctype
        target_doctype = self.target_doctype if is_forward else self.source_doctype
        
        # Use first field mapping as identifier by default
        identifier_mapping = None
        
        for mapping in self.field_mappings:
            source_field = mapping.source_field if is_forward else mapping.target_field
            target_field = mapping.target_field if is_forward else mapping.source_field
            
            # Skip if source field doesn't exist
            if not hasattr(source_doc, source_field):
                continue
                
            identifier_mapping = {"source": source_field, "target": target_field}
            break
            
        if not identifier_mapping:
            # No valid field mapping found
            self.log(
                source_doc, 
                None, 
                "Error", 
                "Forward" if is_forward else "Backward",
                "Update", 
                error_type="Validation",
                error_message="No valid field mapping found for document identification"
            )
            return None
            
        # Get value from source document
        source_value = source_doc.get(identifier_mapping["source"])
        
        if not source_value:
            # No source value to use for identification
            return None
            
        # Find matching target document
        target_docs = frappe.get_all(
            target_doctype,
            filters={identifier_mapping["target"]: source_value},
            fields=["name"]
        )
        
        if target_docs:
            return frappe.get_doc(target_doctype, target_docs[0].name)
            
        return None
        
    def log(self, source_doc, target_doc=None, status="Success", direction="Forward", 
            event="Update", error_type=None, error_message=None, details=None):
        """Log sync activity"""
        if not self.enable_logging:
            return
            
        # Determine log level
        should_log = False
        
        if status == "Error" and self.log_level in ["Error", "Warning", "Info", "Debug"]:
            should_log = True
        elif status == "Skipped" and self.log_level in ["Warning", "Info", "Debug"]:
            should_log = True
        elif status == "Success" and self.log_level in ["Info", "Debug"]:
            should_log = True
            
        if not should_log:
            return
            
        # Prepare source and target information
        source_doctype = source_doc.doctype if hasattr(source_doc, "doctype") else self.source_doctype
        source_name = source_doc.name if hasattr(source_doc, "name") else str(source_doc)
        
        target_doctype = None
        target_name = None
        
        if target_doc:
            target_doctype = target_doc.doctype if hasattr(target_doc, "doctype") else self.target_doctype
            target_name = target_doc.name if hasattr(target_doc, "name") else str(target_doc)
        else:
            target_doctype = self.target_doctype if direction == "Forward" else self.source_doctype
            
        # Create log entry
        log = frappe.new_doc("Sync Log")
        log.update({
            "sync_configuration": self.name,
            "timestamp": now_datetime(),
            "source_doctype": source_doctype,
            "source_doc": source_name,
            "target_doctype": target_doctype,
            "target_doc": target_name or "",
            "status": status,
            "direction": direction,
            "event": event,
            "user": frappe.session.user
        })
        
        if status == "Error":
            log.error_type = error_type or "General"
            log.error_message = error_message
            
        if details:
            log.details = json.dumps(details)
            
        log.insert(ignore_permissions=True)
        
    @frappe.whitelist()
    def test_sync(self, source_doctype=None, source_name=None):
        """Test sync configuration with a sample document"""
        if not source_doctype:
            source_doctype = self.source_doctype
            
        if not source_name:
            # Get a random document from source doctype
            docs = frappe.get_all(source_doctype, limit=1)
            if not docs:
                return {
                    "success": False,
                    "message": f"No documents found in {source_doctype}"
                }
                
            source_name = docs[0].name
            
        try:
            source_doc = frappe.get_doc(source_doctype, source_name)
            
            # Check conditions
            conditions_met = self.should_sync(
                source_doc, 
                "after_update", 
                is_forward=(source_doctype == self.source_doctype)
            )
            
            # Get mapped document
            mapped_doc = self.get_mapped_doc(
                source_doc, 
                is_forward=(source_doctype == self.source_doctype)
            )
            
            # Prepare result for display
            field_mappings = []
            
            for mapping in self.field_mappings:
                source_field = mapping.source_field
                target_field = mapping.target_field
                
                if source_doctype == self.target_doctype:
                    source_field, target_field = target_field, source_field
                    
                value = source_doc.get(source_field)
                mapped_value = mapped_doc.get(target_field)
                
                field_mappings.append({
                    "source_field": source_field,
                    "target_field": target_field,
                    "original_value": value,
                    "mapped_value": mapped_value
                })
                
            # Prepare child table mappings
            child_mappings = []
            
            for mapping in self.child_table_mappings:
                source_table = mapping.source_table
                target_table = mapping.target_table
                
                if source_doctype == self.target_doctype:
                    source_table, target_table = target_table, source_table
                    
                if hasattr(source_doc, source_table):
                    source_rows = source_doc.get(source_table)
                    target_rows = mapped_doc.get(target_table)
                    
                    child_mappings.append({
                        "source_table": source_table,
                        "target_table": target_table,
                        "source_count": len(source_rows),
                        "target_count": len(target_rows),
                        "sample": target_rows[0] if target_rows else {}
                    })
                    
            return {
                "success": True,
                "source_doc": source_name,
                "conditions_met": conditions_met,
                "field_mappings": field_mappings,
                "child_mappings": child_mappings
            }
            
        except Exception as e:
            frappe.log_error(f"Test sync error: {str(e)}\n{traceback.format_exc()}", "Live Sync Test")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
            
    @frappe.whitelist()
    def run_sync_for_document(self, source_doctype, source_name):
        """Manually run sync for a specific document"""
        try:
            if not self.enabled:
                return {
                    "success": False,
                    "message": "This sync configuration is disabled"
                }
                
            source_doc = frappe.get_doc(source_doctype, source_name)
            is_forward = (source_doctype == self.source_doctype)
            
            # Mark document as being synced to prevent loops
            source_doc._syncing = True
            
            if self.should_sync(source_doc, "after_update", is_forward=is_forward):
                # Check for existing target
                target_doc = self.find_matching_target(source_doc, is_forward=is_forward)
                
                if target_doc:
                    # Update existing target
                    mapped_doc = self.get_mapped_doc(source_doc, is_forward=is_forward)
                    
                    # Transfer mapped values to existing doc
                    for field, value in mapped_doc.as_dict().items():
                        if field not in ["name", "owner", "creation", "modified", "modified_by"]:
                            target_doc.set(field, value)
                            
                    # Save target document with sync flag
                    target_doc._syncing = True
                    target_doc.save(ignore_permissions=True)
                    
                    self.log(
                        source_doc, 
                        target_doc, 
                        "Success", 
                        "Forward" if is_forward else "Backward",
                        "Update"
                    )
                    
                    return {
                        "success": True,
                        "message": f"Updated {target_doc.doctype} {target_doc.name}",
                        "target_doctype": target_doc.doctype,
                        "target_name": target_doc.name
                    }
                else:
                    # Create new target
                    target_doc = self.get_mapped_doc(source_doc, is_forward=is_forward)
                    target_doc._syncing = True
                    target_doc.insert(ignore_permissions=True)
                    
                    self.log(
                        source_doc, 
                        target_doc, 
                        "Success", 
                        "Forward" if is_forward else "Backward",
                        "Insert"
                    )
                    
                    return {
                        "success": True,
                        "message": f"Created new {target_doc.doctype} {target_doc.name}",
                        "target_doctype": target_doc.doctype,
                        "target_name": target_doc.name
                    }
            else:
                # Conditions not met
                self.log(
                    source_doc, 
                    None, 
                    "Skipped", 
                    "Forward" if is_forward else "Backward",
                    "Update"
                )
                
                return {
                    "success": False,
                    "message": "Sync conditions not met"
                }
                
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            frappe.log_error(f"Manual sync error: {error_msg}\n{error_trace}", "Live Sync Manual")
            
            self.log(
                {"doctype": source_doctype, "name": source_name}, 
                None, 
                "Error", 
                "Forward" if source_doctype == self.source_doctype else "Backward",
                "Update",
                error_type="System",
                error_message=error_msg
            )
            
            return {
                "success": False,
                "message": f"Error: {error_msg}"
            }
            
    @frappe.whitelist()
    def sync_all_documents(self, batch_size=50):
        """Sync all existing documents"""
        if not self.enabled:
            return {
                "success": False,
                "message": "This sync configuration is disabled"
            }
            
        try:
            # Get documents from source doctype
            docs = frappe.get_all(
                self.source_doctype,
                fields=["name"],
                limit=batch_size
            )
            
            # Track stats
            results = {
                "total": len(docs),
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
                "details": []
            }
            
            # Process batch
            for doc in docs:
                try:
                    result = self.run_sync_for_document(self.source_doctype, doc.name)
                    
                    if result.get("success"):
                        if "Created" in result.get("message", ""):
                            results["created"] += 1
                        else:
                            results["updated"] += 1
                    else:
                        results["skipped"] += 1
                        
                    results["details"].append({
                        "source": doc.name,
                        "status": "Success" if result.get("success") else "Skipped",
                        "message": result.get("message"),
                        "target": result.get("target_name", "")
                    })
                    
                except Exception as e:
                    results["errors"] += 1
                    results["details"].append({
                        "source": doc.name,
                        "status": "Error",
                        "message": str(e)
                    })
                    
            return {
                "success": True,
                "message": f"Processed {results['total']} documents: {results['created']} created, {results['updated']} updated, {results['skipped']} skipped, {results['errors']} errors",
                "results": results
            }
            
        except Exception as e:
            frappe.log_error(f"Batch sync error: {str(e)}\n{traceback.format_exc()}", "Live Sync Batch")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
			}