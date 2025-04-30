import frappe
import json
from frappe.model.document import Document
from frappe.utils import now_datetime, cint
import traceback
import uuid
from frappe.utils.background_jobs import enqueue

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
        """Validate configuration and check for conflicts"""
        self.validate_config()
        self.check_bidirectional_conflicts()
        
    def validate_config(self):
        """Validate configuration against DocType definitions"""
        if not self.source_doctype:
            frappe.throw("Source DocType is required")
            
        if not self.target_doctype:
            frappe.throw("Target DocType is required")
            
        # Make sure config has proper structure
        if not isinstance(self.config, dict):
            self.config = {}
            
        if "direct_fields" not in self.config:
            self.config["direct_fields"] = {}
        
        # 1. Validate identifier mappings
        identifier_mapping = self.config.get("identifier_mapping", {})
        for source_field, target_field in identifier_mapping.items():
            self._validate_field_exists(self.source_doctype, source_field, "Source identifier")
            self._validate_field_exists(self.target_doctype, target_field, "Target identifier")
        
        # 2. Validate direct field mappings
        for source_field, target_field in self.config["direct_fields"].items():
            self._validate_field_exists(self.source_doctype, source_field, "Source")
            self._validate_field_exists(self.target_doctype, target_field, "Target")
        
        # 3. Validate child mappings
        child_mappings = self.config.get("child_mappings", [])
        for mapping in child_mappings:
            source_table = mapping.get("source_table")
            target_table = mapping.get("target_table")
            
            # Validate table fields exist
            if not frappe.get_meta(self.source_doctype).get_field(source_table):
                frappe.throw(f"Source table '{source_table}' does not exist in {self.source_doctype}")
            
            if not frappe.get_meta(self.target_doctype).get_field(target_table):
                frappe.throw(f"Target table '{target_table}' does not exist in {self.target_doctype}")
            
            # Get child doctypes
            source_child_doctype = frappe.get_meta(self.source_doctype).get_field(source_table).options
            target_child_doctype = frappe.get_meta(self.target_doctype).get_field(target_table).options
            
            # Validate field mappings
            for source_field, target_field in mapping.get("fields", {}).items():
                if not frappe.get_meta(source_child_doctype).has_field(source_field):
                    frappe.throw(f"Source field '{source_field}' does not exist in child table {source_child_doctype}")
                
                if not frappe.get_meta(target_child_doctype).has_field(target_field):
                    frappe.throw(f"Target field '{target_field}' does not exist in child table {target_child_doctype}")
            
    def _validate_field_exists(self, doctype, field_path, field_type):
        """Validate that a field exists in the doctype, handling child tables"""
        if field_path == "name":
            return True
            
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
        try:
            existing_syncs = frappe.get_all(
                "Live Sync",
                filters={
                    "source_doctype": self.target_doctype,
                    "target_doctype": self.source_doctype,
                    "bidirectional": 1,
                    "enabled": 1,
                    "name": ["!=", self.name]
                }
            )  # <-- Closing parenthesis added here

            if existing_syncs:
                frappe.throw(f"Circular reference detected with existing sync: {existing_syncs[0].name}")
        except Exception as e:
            frappe.log_error(f"Test sync error: {str(e)}\n{traceback.format_exc()}", "LiveSync Test Error")
            return {"success": False, "message": str(e)}
            
    @frappe.whitelist()
    def trigger_sync_for_document(self, doctype, docname, fast_mode=0):
        """Manually trigger sync for a document"""
        try:
            # Load the document
            doc = frappe.get_doc(doctype, docname)
            
            # Determine direction
            is_forward = (doctype == self.source_doctype)
            
            if cint(fast_mode):
                # Fast mode processing using direct SQL (completely bypassing all validations)
                target_doctype = self.target_doctype if is_forward else self.source_doctype
                result = self._process_fast_sync(doc, is_forward, target_doctype)
                return {
                    "success": True,
                    "message": f"Fast sync completed for {doctype} {docname}{result}"
                }
            else:
                # Standard sync processing
                self.sync_document(doc, "on_update", is_forward)
                
                # Get target doc info for confirmation
                target_info = ""
                target_doctype = self.target_doctype if is_forward else self.source_doctype
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

    def _process_fast_sync(self, source_doc, is_forward, target_doctype):
        """
        Process a single document sync in fast mode using direct SQL operations
        to completely bypass all validations and hooks.
        
        Args:
            source_doc: Source document to sync
            is_forward: Direction of sync 
            target_doctype: Target DocType
            
        Returns:
            String with result information
        """
        # Get field mappings based on direction
        field_mappings = self.config.get("direct_fields", {})
        if not is_forward:
            # Invert mappings for reverse direction
            field_mappings = {v: k for k, v in field_mappings.items()}
            
        # In Frappe, table names are always "tab" + DocType name
        target_table = f"tab{target_doctype}"
        
        # Try to find target document using identifier mappings
        identifier_mapping = self.config.get("identifier_mapping", {})
        if not identifier_mapping:
            # Fallback to first field mapping
            if field_mappings:
                first_src, first_tgt = next(iter(field_mappings.items()))
                identifier_mapping = {first_src: first_tgt}
            
        # Adjust for direction
        if not is_forward:
            identifier_mapping = {v: k for k, v in identifier_mapping.items()}
        
        # Build WHERE clause for finding target
        where_conditions = []
        where_values = []
        
        for src_field, tgt_field in identifier_mapping.items():
            src_value = None
            if src_field == "name":
                src_value = source_doc.name
            elif "." not in src_field:  # Skip hierarchical fields
                src_value = source_doc.get(src_field)
                
            if src_value is not None:
                where_conditions.append(f"`{tgt_field}` = %s")
                where_values.append(src_value)
                
        # If no conditions, try using name
        if not where_conditions:
            where_conditions.append("`name` = %s")
            where_values.append(source_doc.name)
            
        # Build WHERE clause
        where_clause = " AND ".join(where_conditions)
        
        # Check if target exists using direct SQL
        target_exists = False
        target_name = None
        
        # Query for existing record
        if where_clause:
            sql_query = f"SELECT name FROM `{target_table}` WHERE {where_clause} LIMIT 1"
            result = frappe.db.sql(sql_query, tuple(where_values), as_dict=1)
            
            if result:
                target_exists = True
                target_name = result[0].name
        
        # Prepare update data - only include non-null values
        update_fields = []
        update_values = []
        
        for src_field, tgt_field in field_mappings.items():
            if "." not in src_field:  # Skip hierarchical fields in fast mode
                src_value = source_doc.get(src_field)
                if src_value is not None:
                    update_fields.append(tgt_field)
                    update_values.append(src_value)
        
        # Additional required fields for new documents
        if not target_exists:
            # Add standard fields needed for new record
            if "docstatus" not in update_fields:
                update_fields.append("docstatus")
                update_values.append(0)  # Default docstatus is 0 (Draft)
                
            if "owner" not in update_fields:
                update_fields.append("owner")
                update_values.append(frappe.session.user)
                
            if "modified_by" not in update_fields:
                update_fields.append("modified_by")
                update_values.append(frappe.session.user)
                
            if "creation" not in update_fields:
                update_fields.append("creation")
                update_values.append(frappe.utils.now())
                
            if "modified" not in update_fields:
                update_fields.append("modified")
                update_values.append(frappe.utils.now())
                
            # Generate name if not provided
            if "name" not in update_fields:
                # Generate a unique ID for name
                target_name = frappe.generate_hash(length=10)
                update_fields.append("name")
                update_values.append(target_name)
        
        # Execute SQL operation - either UPDATE or INSERT
        if target_exists:
            # UPDATE existing record
            if update_fields:
                # Add modified field
                if "modified" not in update_fields:
                    update_fields.append("modified")
                    update_values.append(frappe.utils.now())
                    
                if "modified_by" not in update_fields:
                    update_fields.append("modified_by")
                    update_values.append(frappe.session.user)
                    
                # Build SET clause
                set_clause = ", ".join([f"`{field}` = %s" for field in update_fields])
                
                # Execute UPDATE
                sql_query = f"UPDATE `{target_table}` SET {set_clause} WHERE name = %s"
                frappe.db.sql(sql_query, tuple(update_values + [target_name]))
                result = f" - Updated {target_doctype} {target_name} using direct SQL (fast mode)"
        else:
            # INSERT new record
            fields_list = ", ".join([f"`{field}`" for field in update_fields])
            values_placeholder = ", ".join(["%s" for _ in update_fields])
            
            # Execute INSERT
            sql_query = f"INSERT INTO `{target_table}` ({fields_list}) VALUES ({values_placeholder})"
            frappe.db.sql(sql_query, tuple(update_values))
            result = f" - Created new {target_doctype} {target_name} using direct SQL (fast mode)"
        
        # Commit changes immediately
        frappe.db.commit()
        
        # Log the sync
        if self.enable_logging:
            frappe.get_doc({
                "doctype": "Sync Log",
                "sync_configuration": self.name,
                "timestamp": frappe.utils.now_datetime(),
                "source_doctype": source_doc.doctype,
                "source_doc": source_doc.name,
                "target_doctype": target_doctype,
                "target_doc": target_name,
                "status": "Success",
                "direction": "Forward" if is_forward else "Backward",
                "event": "Fast SQL Sync",
                "user": frappe.session.user
            }).insert(ignore_permissions=True)
        
        return result
        
    @frappe.whitelist()
    def trigger_bulk_sync(self, source_doctype=None, filters=None, limit=100, fast_mode=False):
        """
        Trigger bulk sync with fast mode option
        
        Args:
            source_doctype: DocType to sync from
            filters: Dictionary of filters to apply
            limit: Maximum number of documents to process
            fast_mode: If True, bypasses validations and hooks for performance
        """
        try:
            # Determine direction
            if not source_doctype:
                source_doctype = self.source_doctype
            is_forward = (source_doctype == self.source_doctype)

            # Parse filters
            if isinstance(filters, str):
                filters = json.loads(filters)
            filters = filters or {}

            # Apply delta filter
            last_key = 'last_synced_forward' if is_forward else 'last_synced_backward'
            last_sync = getattr(self, last_key, None)
            if last_sync:
                filters['modified'] = ['>', last_sync]

            # Fetch docs - only names and modified for efficiency
            docs = frappe.get_all(
                source_doctype,
                filters=filters,
                limit=int(limit),
                fields=["name", "modified"],
                order_by="modified ASC"
            )
            
            if not docs:
                return {'success': False,
                        'message': f'No documents found matching filters in {source_doctype}'}

            # Generate job ID for larger batches
            job_id = f"bulk_sync_{uuid.uuid4().hex[:8]}"
            
            # For larger batches (>10 docs), use background processing
            if len(docs) > 10:
                # Store job information in cache
                job_data = {
                    "total": len(docs),
                    "processed": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "status": "Queued",
                    "start_time": frappe.utils.now(),
                    "sync_config": self.name,
                    "source_doctype": source_doctype,
                    "direction": "Forward" if is_forward else "Backward",
                    "fast_mode": cint(fast_mode)
                }
                
                # Set cache with single operation
                frappe.cache().set_value(f"bs:{job_id}", json.dumps(job_data), expires_in_sec=3600)

                # Queue background job
                enqueue(
                    'core.sync_handler.process_bulk_sync',
                    queue='long',
                    timeout=3600,
                    sync_config=self.name,
                    source_doctype=source_doctype,
                    doc_names=[d.name for d in docs],
                    is_forward=is_forward,
                    job_id=job_id,
                    fast_mode=cint(fast_mode),
                    now=False
                )

                return {
                    'success': True,
                    'message': f'Bulk sync of {len(docs)} documents queued as job {job_id}.',
                    'job_id': job_id,
                    'total_docs': len(docs)
                }

            # For smaller batches, process directly
            processed, succeeded, failed = 0, 0, 0
            details = []
            
            # Fast mode implementation - direct DB operations
            if cint(fast_mode):
                # Process using direct DB operations
                results = self._process_bulk_sync_fast_mode(
                    source_doctype, [d.name for d in docs], is_forward
                )
                
                return {
                    'success': True,
                    'message': f'Fast mode processed {results["succeeded"]} docs successfully, {results["failed"]} failed',
                    'results': results
                }
            
            # Standard mode - process with full ORM
            for doc_name in [d.name for d in docs]:
                try:
                    # Get full document
                    doc = frappe.get_doc(source_doctype, doc_name)
                    
                    # Process sync
                    self.sync_document(doc, "on_update", is_forward)
                    
                    succeeded += 1
                    details.append({"name": doc_name, "status": "Success"})
                except Exception as e:
                    failed += 1
                    details.append({"name": doc_name, "status": "Failed", "error": str(e)})
                    frappe.log_error(
                        f"Error syncing {source_doctype} {doc_name}: {str(e)}",
                        "Bulk Sync Error"
                    )
                
                processed += 1
                
            # Update last sync timestamp
            now = frappe.utils.now_datetime()
            setattr(self, last_key, now)
            self.db_set(last_key, now, update_modified=False)
            
            # Return results
            results = {
                'total': len(docs),
                'processed': processed,
                'succeeded': succeeded,
                'failed': failed,
                'details': details
            }
            
            return {
                'success': True,
                'message': f'Processed {processed} docs: {succeeded} succeeded, {failed} failed',
                'results': results
            }

        except Exception as e:
            frappe.log_error(f'Bulk sync error: {str(e)}\n{traceback.format_exc()}', 'LiveSync Bulk Error')
            return {'success': False, 'message': str(e)}
            
    def _process_bulk_sync_fast_mode(self, source_doctype, doc_names, is_forward):
        """
        Process bulk sync in fast mode using direct DB operations
        
        Args:
            source_doctype: DocType to sync from
            doc_names: List of document names to process
            is_forward: Direction of sync
            
        Returns:
            Dictionary with results
        """
        processed = 0
        succeeded = 0
        failed = 0
        details = []
        
        # Determine target doctype
        target_doctype = self.target_doctype if is_forward else self.source_doctype
        
        # Get field mappings based on direction
        field_mappings = self.config.get("direct_fields", {})
        if not is_forward:
            # Invert mappings for reverse direction
            field_mappings = {v: k for k, v in field_mappings.items()}
            
        # Process in batches of 50 for better performance
        batch_size = 50
        for i in range(0, len(doc_names), batch_size):
            batch = doc_names[i:i+batch_size]
            batch_data = {}
            
            # Fetch source documents in batch
            source_docs = frappe.get_all(
                source_doctype,
                filters={"name": ["in", batch]},
                fields=["name"] + list(field_mappings.keys())
            )
            
            for source_doc in source_docs:
                try:
                    # Find target document
                    target_filters = {}
                    
                    # Use identifier mapping if available
                    identifier_mapping = self.config.get("identifier_mapping", {})
                    if not identifier_mapping:
                        # Fallback to first field mapping
                        first_src, first_tgt = next(iter(field_mappings.items()))
                        identifier_mapping = {first_src: first_tgt}
                        
                    # Adjust for direction
                    if not is_forward:
                        identifier_mapping = {v: k for k, v in identifier_mapping.items()}
                    
                    # Build target filters
                    for src_field, tgt_field in identifier_mapping.items():
                        if hasattr(source_doc, src_field) and source_doc.get(src_field):
                            target_filters[tgt_field] = source_doc.get(src_field)
                            
                    # If no filters, try using name
                    if not target_filters:
                        target_filters["name"] = source_doc.name
                        
                    # Check if target exists
                    target_exists = frappe.db.exists(target_doctype, target_filters)
                    
                    # Prepare update data
                    update_data = {}
                    for src_field, tgt_field in field_mappings.items():
                        if hasattr(source_doc, src_field) and source_doc.get(src_field) is not None:
                            update_data[tgt_field] = source_doc.get(src_field)
                            
                    # No child tables in fast mode
                    
                    if target_exists:
                        # Update existing document using db_set
                        for field, value in update_data.items():
                            frappe.db.set_value(target_doctype, target_filters, field, value)
                    else:
                        # Create new document directly in DB
                        update_data["doctype"] = target_doctype
                        new_doc = frappe.get_doc(update_data)
                        new_doc.insert(ignore_permissions=True)
                        
                    # Success
                    succeeded += 1
                    details.append({"name": source_doc.name, "status": "Success"})
                        
                except Exception as e:
                    # Failed
                    failed += 1
                    details.append({"name": source_doc.name, "status": "Failed", "error": str(e)})
                    
                processed += 1
                
            # Commit after each batch
            frappe.db.commit()
        
        # Update last sync timestamp
        last_key = 'last_synced_forward' if is_forward else 'last_synced_backward'
        now = frappe.utils.now_datetime()
        self.db_set(last_key, now, update_modified=False)
        
        # Return results
        return {
            'total': len(doc_names),
            'processed': processed,
            'succeeded': succeeded,
            'failed': failed,
            'details': details
        }
        
        if existing_syncs:
            frappe.throw(f"Circular reference detected with existing sync: {existing_syncs[0].name}")
            
    def on_update(self):
        """Clear cache when configuration changes"""
        self.clear_sync_cache()
        
    def clear_sync_cache(self):
        """Clear sync cache for affected doctypes"""
        # Clear cache for source doctype
        frappe.cache().delete_value(f"sync_configs_for_{self.source_doctype}")
        
        # Clear cache for target doctype if bidirectional
        if self.bidirectional:
            frappe.cache().delete_value(f"sync_configs_for_{self.target_doctype}")
            
    def find_matching_document(self, source_doc, is_forward=True):
        """Find matching document in target doctype efficiently"""
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
        
        # Build filters for query
        filters = []
        for src_field, tgt_field in identifier_mapping.items():
            # Adjust fields based on direction
            if is_forward:
                source_field, target_field = src_field, tgt_field
            else:
                source_field, target_field = tgt_field, src_field
            
            # Skip hierarchical fields in main filter
            if "." in source_field or "." in target_field:
                continue
                
            # Get source value - special handling for 'name'
            source_value = None
            if source_field == "name":
                source_value = source_doc.name
            else:
                source_value = source_doc.get(source_field)
            
            # Skip if no value
            if source_value is None:
                continue
                
            # Add to filters
            filters.append([target_doctype, target_field, "=", source_value])
        
        # Perform query if we have filters
        if filters:
            # Use OR for multiple filters
            if len(filters) > 1:
                filters = [["OR"] + filters]
                
            target_docs = frappe.get_all(
                target_doctype,
                filters=filters,
                fields=["name"],
                limit=1
            )
            
            if target_docs:
                return frappe.get_doc(target_doctype, target_docs[0].name)
        
        # Additional fallback: check for document with matching name
        if frappe.db.exists(target_doctype, source_doc.name):
            return frappe.get_doc(target_doctype, source_doc.name)
        
        # No match found
        return None
            
    @frappe.whitelist()
    def sync_document(self, doc, event, is_forward=True):
        """
        Core sync entrypoint: called on insert/update or via Test Sync.
        Optimized for better performance with early filtering.
        """
        # Skip if already syncing or not enabled
        if getattr(doc, "_syncing", False) or not self.enabled:
            return

        # Handle deletion separately (no need to reload)
        if event == "on_trash":
            self._handle_delete(doc, is_forward)
            return
        
        # Skip if source doesn't match conditions
        if not self._check_sync_conditions(doc, is_forward):
            return
            
        # Determine target doctype
        target_doctype = self.target_doctype if is_forward else self.source_doctype

        # Before sync hook
        if self.config.get("hooks", {}).get("before_sync"):
            hook_name = self.config["hooks"]["before_sync"]
            try:
                hook = frappe.get_attr(hook_name)
                hook(doc, is_forward, self)
            except Exception as e:
                frappe.log_error(f"Error in before_sync hook: {str(e)}", "LiveSync Hook Error")

        # Find target efficiently
        target_doc = self.find_matching_document(doc, is_forward)
        if not target_doc:
            target_doc = frappe.new_doc(target_doctype)

        # Prevent loops, mark syncing
        target_doc._syncing = True

        try:
            # Process fields and save
            self._handle_insert_or_update(doc, event, is_forward, target_doc)
        finally:
            target_doc._syncing = False
            
    def _check_sync_conditions(self, doc, is_forward):
        """Quick check if doc meets sync conditions"""
        conditions = self.config.get("conditions", {})
        if not conditions:
            return True
            
        # Get skip conditions
        skip_if = conditions.get("skip_if", [])
        
        # Check skip conditions first (early exit)
        for condition in skip_if:
            if len(condition) != 3:
                continue
                
            field, op, value = condition
            doc_val = doc.get(field)
            
            if op == "==" and doc_val == value:
                return False
            elif op == "!=" and doc_val != value:
                return False
            elif op == "in" and doc_val in value:
                return False
            elif op == "not in" and doc_val not in value:
                return False
                
        # Check required conditions
        only_if = conditions.get("only_if", [])
        for condition in only_if:
            if len(condition) != 3:
                continue
                
            field, op, value = condition
            doc_val = doc.get(field)
            
            if op == "==" and doc_val != value:
                return False
            elif op == "!=" and doc_val == value:
                return False
            elif op == "in" and doc_val not in value:
                return False
            elif op == "not in" and doc_val in value:
                return False
                
        return True
            
    def _handle_insert_or_update(self, source_doc, event, is_forward, target_doc):
        """
        Given a source_doc and target_doc, map all fields & child tables, then save.
        """
        # 1) Field mappings
        self._process_field_mappings(source_doc, target_doc, is_forward)

        # 2) Child-table mappings
        self._process_child_tables(source_doc, target_doc, is_forward)

        # 3) Save or insert
        if target_doc.get("__islocal"):
            target_doc.insert(ignore_permissions=True)
            action = "Insert"
        else:
            target_doc.save(ignore_permissions=True)
            action = "Update"

        # 4) Hooks after sync
        if self.config.get("hooks", {}).get("after_sync"):
            hook_name = self.config["hooks"]["after_sync"]
            try:
                hook = frappe.get_attr(hook_name)
                hook(source_doc, target_doc, is_forward, self)
            except Exception as e:
                frappe.log_error(f"Error in after_sync hook: {str(e)}", "LiveSync Hook Error")

        # 5) Log it
        self._log_sync(source_doc, target_doc, action, is_forward)

    def _apply_transform(self, field_name, value, doc):
        """Apply transformation to a field value"""
        transform_config = self.config.get("transform", {})
        
        if field_name in transform_config:
            transform_name = transform_config[field_name]
            
            try:
                transform_function = frappe.get_attr(transform_name)
                return transform_function(value, doc)
            except Exception as e:
                frappe.log_error(
                    f"Error applying transform {transform_name} to {field_name}: {str(e)}",
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
            self._log_sync(doc, target_doc, "Delete", is_forward)
        elif delete_action == "Archive":
            # Set status to archived
            if hasattr(target_doc, "status"):
                target_doc.status = "Archived"
                target_doc.save(ignore_permissions=True)
                self._log_sync(doc, target_doc, "Archive", is_forward)
        elif delete_action == "Set Field" and hasattr(self, "on_delete_field"):
            # Set specified field to mark as deleted
            field_name = self.on_delete_field
            if hasattr(target_doc, field_name):
                target_doc.set(field_name, 1)
                target_doc.save(ignore_permissions=True)
                self._log_sync(doc, target_doc, "Set Field", is_forward)
                
    def _process_child_tables(self, source_doc, target_doc, is_forward=True):
        """Process child table mappings efficiently"""
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
                continue
                
            # Check if source table exists in source document
            if not hasattr(source_doc, source_table):
                continue
                
            # Get source rows
            source_rows = source_doc.get(source_table, [])
            
            # Get target child table doctype
            try:
                child_doctype = frappe.get_meta(target_doc.doctype).get_field(target_table).options
            except Exception:
                continue
                
            # Create target rows
            target_rows = []
            for source_row in source_rows:
                # Create a new row
                row_dict = {"doctype": child_doctype, "parentfield": target_table}
                
                # Map fields efficiently
                for src_field, tgt_field in fields.items():
                    source_value = getattr(source_row, src_field, None)
                    if source_value is None and hasattr(source_row, "get"):
                        source_value = source_row.get(src_field)
                        
                    if source_value is not None:
                        row_dict[tgt_field] = source_value
                
                # Add the row
                target_rows.append(row_dict)
            
            # Replace all rows in one operation
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
            "event": action,
            "user": frappe.session.user
        }).insert(ignore_permissions=True)
        
    def _process_field_mappings(self, source_doc, target_doc, is_forward=True):
        """Process all field mappings with optimization for standard fields"""
        # Build a batch of standard field updates
        updates = {}
        
        # Process identifier mapping
        identifier_mapping = self.config.get("identifier_mapping", {})
        if identifier_mapping:
            for src_field, tgt_field in identifier_mapping.items():
                # Adjust fields based on direction
                if is_forward:
                    source_field, target_field = src_field, tgt_field
                else:
                    source_field, target_field = tgt_field, src_field
                
                # Skip hierarchical fields for standard updates
                if "." in source_field or "." in target_field:
                    continue
                    
                # Get and update value
                source_value = source_doc.get(source_field)
                if source_value is not None:
                    updates[target_field] = source_value
        
        # Process regular field mappings (standard fields)
        field_mappings = self.config.get("direct_fields", {})
        for src_field, tgt_field in field_mappings.items():
            # Adjust fields based on direction
            if is_forward:
                source_field, target_field = src_field, tgt_field
            else:
                source_field, target_field = tgt_field, src_field
            
            # Skip hierarchical fields for standard updates
            if "." in source_field or "." in target_field:
                continue
                
            # Get value and apply transforms
            source_value = source_doc.get(source_field)
            if source_value is not None:
                # Apply transform if configured
                transform_config = self.config.get("transform", {})
                if source_field in transform_config:
                    source_value = self._apply_transform(source_field, source_value, source_doc)
                    
                updates[target_field] = source_value
        
        # Apply all standard field updates at once
        for field, value in updates.items():
            target_doc.set(field, value)
        
        # Process hierarchical fields in a second pass
        for src_field, tgt_field in field_mappings.items():
            # Adjust fields based on direction
            if is_forward:
                source_field, target_field = src_field, tgt_field
            else:
                source_field, target_field = tgt_field, src_field
            
            # Only process hierarchical fields
            if "." in source_field or "." in target_field:
                self._map_hierarchical_fields(source_doc, target_doc, source_field, target_field)
    
    def _map_hierarchical_fields(self, source_doc, target_doc, source_field, target_field):
        """Map hierarchical fields (parent-child relationships)"""
        # Handle different combinations of hierarchical fields
        if "." in source_field and "." in target_field:
            # Child to child mapping
            source_value = self._get_hierarchical_field_value(source_doc, source_field)
            if source_value is not None:
                self._set_hierarchical_field_value(target_doc, target_field, source_value)
        elif "." in source_field:
            # Child to parent mapping
            source_value = self._get_hierarchical_field_value(source_doc, source_field)
            if source_value is not None:
                target_doc.set(target_field, source_value)
        elif "." in target_field:
            # Parent to child mapping
            source_value = source_doc.get(source_field)
            if source_value is not None:
                self._set_hierarchical_field_value(target_doc, target_field, source_value)
                
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
        """Set value in a hierarchical field path efficiently"""
        # Parse the field path
        path_info = self._parse_table_reference(field_path)
        table_name = path_info["table"]
        field_name = path_info["field"]
        index = path_info["index"]
        
        # Make sure the table field exists in the doctype
        meta = frappe.get_meta(doc.doctype)
        table_field = meta.get_field(table_name)
        if not table_field:
            return

        # Get the child doctype
        child_doctype = table_field.options
        
        # Get existing child table
        child_table = doc.get(table_name, [])
        
        # Determine which row to update or create
        if index is not None:
            # Specific index requested
            while len(child_table) <= index:
                # Create new rows until we reach the desired index
                new_row = frappe.new_doc(child_doctype)
                new_row.parentfield = table_name
                child_table.append(new_row)
            
            # Update the specified row
            child_table[index].set(field_name, value)
        else:
            # No index specified, use first row or create one
            if not child_table:
                # Create first row if table is empty
                new_row = frappe.new_doc(child_doctype)
                new_row.parentfield = table_name
                new_row.set(field_name, value)
                child_table.append(new_row)
            else:
                # Update existing first row
                child_table[0].set(field_name, value)
        
        # Update the table in one operation
        doc.set(table_name, child_table)

    def _parse_table_reference(self, field_path):
        """Parse a field path with potential index, like "details[0].field1" or "details.field1" """
        import re
        
        # Split into table part and field part
        parts = field_path.split(".")
        if len(parts) != 2:
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
                source_value = source_doc.get(source_field) if "." not in source_field else self._get_hierarchical_field_value(source_doc, source_field)
                
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
                        sample_value = getattr(source_rows[0], src_field, None)
                        if sample_value is None and hasattr(source_rows[0], "get"):
                            sample_value = source_rows[0].get(src_field)
                            
                        if sample_value is not None:
                            sample_data[src_field] = sample_value
                
                child_mappings.append({
                    "source_table": source_table,
                    "target_table": target_table,
                    "row_count": row_count,
                    "fields": fields,
                    "sample_data": sample_data
                })