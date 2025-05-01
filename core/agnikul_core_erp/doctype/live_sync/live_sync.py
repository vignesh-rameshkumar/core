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
        """
        Manually trigger sync for a document
        
        Args:
            doctype: Source document type
            docname: Source document name
            fast_mode: If 1, use direct SQL operations for better performance
        """
        try:
            # Load the document
            doc = frappe.get_doc(doctype, docname)
            
            # Determine direction
            is_forward = (doctype == self.source_doctype)
            target_doctype = self.target_doctype if is_forward else self.source_doctype
            
            if cint(fast_mode):
                # Fast mode processing using direct SQL
                result = self._process_fast_sync(doc, is_forward, target_doctype)
                return {
                    "success": True,
                    "message": f"Fast sync completed for {doctype} {docname}{result}"
                }
            else:
                # Standard sync processing with optimized field-level updates
                self.sync_document(doc, "on_update", is_forward)
                
                # Get target doc info for confirmation
                target_info = ""
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
        to completely bypass all validations and hooks, while properly handling name sync.
        
        Args:
            source_doc: Source document to sync
            is_forward: Direction of sync 
            target_doctype: Target DocType
            
        Returns:
            String with result information
        """
        # Check for sync_name hook first - it affects target document name
        target_name = source_doc.name  # Default to same name
        sync_name_hook_executed = False
        
        if self.config.get("hooks", {}).get("sync_name"):
            try:
                hook_name = self.config["hooks"]["sync_name"]
                hook_function = frappe.get_attr(hook_name)
                
                # Create a minimal temporary document for the hook
                temp_target_doc = frappe.new_doc(target_doctype)
                temp_target_doc._for_fast_sync = True
                
                # Call the hook and get the target name
                result_doc = hook_function(source_doc, temp_target_doc, is_forward, self)
                
                if result_doc and hasattr(result_doc, 'name'):
                    target_name = result_doc.name
                    sync_name_hook_executed = True
            except Exception as e:
                frappe.log_error(f"Error in sync_name hook: {str(e)}", "FastSync Hook Error")
        
        # Execute before_sync hooks (if configured)
        before_sync_executed = False
        if self.config.get("hooks", {}).get("before_sync"):
            try:
                hook_name = self.config["hooks"]["before_sync"]
                hook_function = frappe.get_attr(hook_name)
                hook_function(source_doc, is_forward, self)
                before_sync_executed = True
            except Exception as e:
                frappe.log_error(f"Error in before_sync hook: {str(e)}", "FastSync Hook Error")
        
        # In Frappe, table names are always "tab" + DocType name
        target_table = f"tab{target_doctype}"
        
        # Check if target already exists
        target_exists = False
        existing_target_name = None
        
        # 1. First check if there's a document with the target_name
        if target_name:
            target_exists = frappe.db.exists(target_doctype, target_name)
            if target_exists:
                existing_target_name = target_name
        
        # 2. If not found and we didn't use sync_name hook, try identifier mappings
        if not target_exists and not sync_name_hook_executed:
            identifier_mapping = self.config.get("identifier_mapping", {})
            if not identifier_mapping:
                # Fallback to first field mapping
                field_mappings = self.config.get("direct_fields", {})
                if not is_forward:
                    field_mappings = {v: k for k, v in field_mappings.items()}
                    
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
            
            # Query for existing record
            if where_conditions:
                where_clause = " AND ".join(where_conditions)
                sql_query = f"SELECT name FROM `{target_table}` WHERE {where_clause} LIMIT 1"
                result = frappe.db.sql(sql_query, tuple(where_values), as_dict=1)
                
                if result:
                    target_exists = True
                    existing_target_name = result[0].name
        
        # If target exists, use its name, otherwise use the target_name from hook
        if target_exists:
            target_name = existing_target_name
        
        # Process field mappings - returning fields and values for parent document update
        # and additional mappings for parent-to-child fields
        update_fields, update_values, parent_to_child = self._fast_process_field_mappings(
            source_doc, target_doctype, target_name, is_forward
        )
        
        # Override name if set by sync_name hook
        if sync_name_hook_executed and "name" not in update_fields:
            update_fields.append("name")
            update_values.append(target_name)
        
        # Execute SQL operation - either UPDATE or INSERT for parent document
        if target_exists:
            # UPDATE existing record
            if update_fields:
                # Add modified field if not present
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
                operation = "Updated"
            else:
                operation = "No changes to"
        else:
            # Additional required fields for new documents
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
                
            # Set name explicitly if not already in fields
            if "name" not in update_fields and target_name:
                update_fields.append("name")
                update_values.append(target_name)
            elif "name" not in update_fields:
                # Generate a random name if not provided by hook
                target_name = frappe.generate_hash(length=10)
                update_fields.append("name")
                update_values.append(target_name)
            else:
                # Get name from the update values
                name_index = update_fields.index("name")
                target_name = update_values[name_index]
            
            # INSERT new record
            if update_fields:
                fields_list = ", ".join([f"`{field}`" for field in update_fields])
                values_placeholder = ", ".join(["%s"] * len(update_fields))
                
                # Execute INSERT
                sql_query = f"INSERT INTO `{target_table}` ({fields_list}) VALUES ({values_placeholder})"
                frappe.db.sql(sql_query, tuple(update_values))
                operation = "Created"
            else:
                operation = "Failed to create"
        
        # Process child tables if parent record exists
        if target_name and operation != "Failed to create":
            # Process standard child tables
            self._fast_process_child_tables(source_doc, target_name, target_doctype, is_forward)
            
            # Process parent to child mappings
            self._fast_process_parent_to_child(source_doc, target_doctype, target_name, parent_to_child, is_forward)
        
        # Commit changes
        frappe.db.commit()
        
        # Execute after_sync hooks if configured
        if target_name and self.config.get("hooks", {}).get("after_sync"):
            try:
                # Create temporary target doc for the hook
                target_doc = None
                try:
                    # Try to fetch the actual document
                    target_doc = frappe.get_doc(target_doctype, target_name)
                except:
                    # If fetch fails, create a stub with basic properties
                    target_doc = type('obj', (object,), {
                        'doctype': target_doctype,
                        'name': target_name,
                        'get': lambda self, key, default=None: default
                    })()
                
                hook_name = self.config["hooks"]["after_sync"]
                hook_function = frappe.get_attr(hook_name)
                hook_function(source_doc, target_doc, is_forward, self)
            except Exception as e:
                frappe.log_error(f"Error in after_sync hook: {str(e)}", "FastSync Hook Error")
        
        # Log the sync
        if self.enable_logging:
            frappe.get_doc({
                "doctype": "Sync Log",
                "sync_configuration": self.name,
                "timestamp": frappe.utils.now_datetime(),
                "source_doctype": source_doc.doctype,
                "source_doc": source_doc.name,
                "target_doctype": target_doctype,
                "target_doc": target_name or "Failed",
                "status": "Success" if target_name else "Error",
                "direction": "Forward" if is_forward else "Backward",
                "event": "Fast SQL Sync" + (" with hooks" if before_sync_executed or sync_name_hook_executed else ""),
                "user": frappe.session.user
            }).insert(ignore_permissions=True)
        
        # Return result message
        hook_info = " with hooks" if before_sync_executed or sync_name_hook_executed else ""
        return f" - {operation} {target_doctype} {target_name} using direct SQL (fast mode{hook_info})"
        
    @frappe.whitelist()
    def trigger_bulk_sync(self, source_doctype=None, filters=None, limit=100, fast_mode=0):
        """
        Trigger delta-aware bulk sync while preserving hooks/validations
        
        Args:
            source_doctype: DocType to sync from
            filters: Dictionary of filters to apply
            limit: Maximum documents to process
            fast_mode: If 1, use direct SQL for better performance and bypass validations
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

            # Fetch only document names for efficiency
            docs = frappe.get_all(
                source_doctype,
                filters=filters,
                limit=int(limit),
                fields=["name"],
                order_by="modified ASC"
            )
            
            if not docs:
                return {'success': False,
                        'message': f'No documents found matching filters in {source_doctype}'}

            # Generate job ID
            job_id = f"bulk_sync_{uuid.uuid4().hex[:10]}"
            
            # For larger batches, enqueue background job
            if len(docs) > 10:
                cache_key = f"bs:{job_id}"
                frappe.cache().set_value(f"{cache_key}:total", len(docs))
                frappe.cache().set_value(f"{cache_key}:processed", 0)
                frappe.cache().set_value(f"{cache_key}:succeeded", 0)
                frappe.cache().set_value(f"{cache_key}:failed", 0)
                frappe.cache().set_value(f"{cache_key}:status", "Queued")
                frappe.cache().set_value(f"{cache_key}:start_time", frappe.utils.now())
                frappe.cache().set_value(f"{cache_key}:sync_config", self.name)
                frappe.cache().set_value(f"{cache_key}:source_doctype", source_doctype)
                frappe.cache().set_value(f"{cache_key}:direction", "Forward" if is_forward else "Backward")
                frappe.cache().set_value(f"{cache_key}:fast_mode", cint(fast_mode))

                frappe.enqueue(
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

            # Small batch - process directly
            processed, succeeded, failed = 0, 0, 0
            details = []
            
            target_doctype = self.target_doctype if is_forward else self.source_doctype
            
            # Process in batch for better performance
            for doc_name in [d.name for d in docs]:
                try:
                    # Get document
                    source_doc = frappe.get_doc(source_doctype, doc_name)
                    
                    if cint(fast_mode):
                        # Use fast mode with direct SQL
                        result = self._process_fast_sync(source_doc, is_forward, target_doctype)
                        succeeded += 1
                        details.append({"name": doc_name, "status": "Success"})
                    else:
                        # Standard sync
                        self.sync_document(source_doc, "on_update", is_forward)
                        succeeded += 1
                        details.append({"name": doc_name, "status": "Success"})
                except Exception as e:
                    failed += 1
                    details.append({"name": doc_name, "status": "Failed", "error": str(e)})
                    frappe.log_error(
                        f"Error syncing {source_doctype} {doc_name}: {str(e)}\n{traceback.format_exc()}",
                        "Bulk Sync Error"
                    )
                
                processed += 1
                    
            # Only update last_synced if there were successful syncs
            if succeeded > 0:
                now = frappe.utils.now_datetime()
                setattr(self, last_key, now)
                self.db_set(last_key, now, update_modified=False)

            # Return results
            results = {
                'total': len(docs),
                'processed': processed,
                'succeeded': succeeded,
                'failed': failed,
                'details': details,
                'fast_mode': cint(fast_mode)
            }

            return {
                'success': True,
                'message': f'Processed {processed} docs: {succeeded} succeeded, {failed} failed' + (' using fast mode' if cint(fast_mode) else ''),
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
            
    def sync_document(self, doc, event, is_forward=True):
        """
        Core sync entrypoint: called on insert/update or via Test Sync.
        Always reloads the source, ensures correct target name, then maps & saves.
        """
        # 1) Skip if already syncing or not enabled
        if getattr(doc, "_syncing", False) or not self.enabled:
            return

        # 2) Skip if event is backward but this is not bidirectional
        if event == "backward" and not self.bidirectional:
            return

        # 3) Skip if conditions do not match
        if not self._check_sync_conditions(doc, is_forward):
            return

        # 4) Reload the source so we sync its final saved state
        try:
            doc = frappe.get_doc(doc.doctype, doc.name)
        except frappe.DoesNotExistError:
            # Handle deletion - nothing to do if deleted
            if event == "on_trash":
                self._handle_delete(doc, is_forward)
            return

        # 5) Determine target doctype based on direction
        target_doctype = self.target_doctype if is_forward else self.source_doctype

        # 6) Execute before_sync hooks if configured
        if self.config.get("hooks", {}).get("before_sync"):
            try:
                hook_name = self.config["hooks"]["before_sync"]
                hook_function = frappe.get_attr(hook_name)
                hook_function(doc, is_forward, self)
            except Exception as e:
                frappe.log_error(f"Error in before_sync hook: {str(e)}", "LiveSync Hook Error")

        # 7) Apply sync_name hook FIRST (if configured)
        # This is important: we apply sync_name hook before finding the matching document
        # to ensure proper handling of document creation/naming
        target_doc = None
        sync_name_used = False
        
        if self.config.get("hooks", {}).get("sync_name"):
            try:
                hook_name = self.config["hooks"]["sync_name"]
                hook_function = frappe.get_attr(hook_name)
                
                # Create a minimal target doc to pass to the hook
                temp_target_doc = frappe.new_doc(target_doctype)
                
                # Call the sync_name hook to get target with the correct name
                result_doc = hook_function(doc, temp_target_doc, is_forward, self)
                
                # If sync_name hook returned a document, use it as our target
                if result_doc and hasattr(result_doc, 'name'):
                    target_doc = result_doc
                    sync_name_used = True
                    
                    # Check if the document was already inserted by the hook
                    if hasattr(target_doc, "__islocal") and not target_doc.__islocal:
                        # Document is already in the database
                        pass
            except Exception as e:
                frappe.log_error(f"Error in sync_name hook: {str(e)}", "LiveSync Hook Error")
        
        # 8) Find or create target doc (if not created by sync_name hook)
        if not target_doc:
            target_doc = self.find_matching_document(doc, is_forward)
            if not target_doc:
                target_doc = frappe.new_doc(target_doctype)

        # 9) Prevent loops, mark syncing
        target_doc._syncing = True

        try:
            # 10) Process all field mappings
            self._process_field_mappings(doc, target_doc, is_forward)

            # 11) Process child tables
            self._process_child_tables(doc, target_doc, is_forward)

            # 12) Save the target document
            # Check if document needs to be inserted or updated
            is_new = target_doc.get("__islocal", True)
            
            # For documents returned by sync_name hook that might already be inserted
            if is_new:
                # Double-check we're not trying to insert a document that already exists
                if frappe.db.exists(target_doctype, target_doc.name):
                    # Load the existing document and update it instead
                    target_doc = frappe.get_doc(target_doctype, target_doc.name)
                    self._process_field_mappings(doc, target_doc, is_forward)
                    self._process_child_tables(doc, target_doc, is_forward)
                    target_doc._syncing = True
                    target_doc.save(ignore_permissions=True)
                    action = "Update"
                else:
                    # Insert new document
                    target_doc.insert(ignore_permissions=True)
                    action = "Insert"
            else:
                # Update existing document
                target_doc.save(ignore_permissions=True)
                action = "Update"

            # 13) Execute after_sync hooks if configured
            if self.config.get("hooks", {}).get("after_sync"):
                try:
                    hook_name = self.config["hooks"]["after_sync"]
                    hook_function = frappe.get_attr(hook_name)
                    hook_function(doc, target_doc, is_forward, self)
                except Exception as e:
                    frappe.log_error(f"Error in after_sync hook: {str(e)}", "LiveSync Hook Error")

            # 14) Log the sync
            self._log_sync(doc, target_doc, action, is_forward)
            
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
        """
        Process child table mappings efficiently by only updating changed fields.
        Supports key-based matching to identify corresponding rows.
        """
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
                
            # Get existing target rows
            target_rows = target_doc.get(target_table, [])
            
            # Determine key field for matching rows
            key_field = mapping.get("key_field")
            
            # If no key field specified, try to find a suitable one
            if not key_field:
                # Try to find a field that's used for mapping and exists in both source and target
                for src_field, tgt_field in fields.items():
                    if src_field in [f.fieldname for f in frappe.get_meta(child_doctype).fields]:
                        key_field = src_field
                        break
                
                # If still no key field, use idx as fallback (position-based matching)
                if not key_field:
                    key_field = "idx"
            
            # Create dictionaries for easier lookup
            # For source: key is the value of key_field, value is the row
            source_dict = {}
            for i, row in enumerate(source_rows):
                key_value = row.get(key_field) if key_field != "idx" else i+1
                if key_value:
                    source_dict[key_value] = row
            
            # For target: key is the value of key_field, value is the row
            target_dict = {}
            for i, row in enumerate(target_rows):
                key_value = row.get(key_field) if key_field != "idx" else i+1
                if key_value:
                    target_dict[key_value] = row
            
            # Track rows to keep
            rows_to_keep = []
            
            # Process source rows to update existing or create new
            for src_key, src_row in source_dict.items():
                if src_key in target_dict:
                    # Update existing row
                    target_row = target_dict[src_key]
                    
                    # Update only changed fields
                    changed = False
                    for src_field, tgt_field in fields.items():
                        src_value = src_row.get(src_field)
                        current_value = target_row.get(tgt_field)
                        
                        # Only update if values differ
                        if src_value != current_value:
                            target_row.set(tgt_field, src_value)
                            changed = True
                    
                    # Keep track of this row
                    rows_to_keep.append(target_row)
                else:
                    # Create new row
                    new_row = frappe.new_doc(child_doctype)
                    for src_field, tgt_field in fields.items():
                        src_value = src_row.get(src_field)
                        if src_value is not None:
                            new_row.set(tgt_field, src_value)
                    
                    # Set the key field if it's in the target fields
                    if key_field in fields.values():
                        # Find the source field that maps to key_field
                        for s_field, t_field in fields.items():
                            if t_field == key_field:
                                key_value = src_row.get(s_field)
                                new_row.set(key_field, key_value)
                                break
                    
                    # Add to rows to keep
                    rows_to_keep.append(new_row)
            
            # Update target_doc with the rows to keep
            target_doc.set(target_table, rows_to_keep)

    def _fast_process_child_tables(self, source_doc, target_name, target_doctype, is_forward=True):
        """
        Process child tables using direct SQL operations in fast mode.
        Only updates changed fields and supports key-based matching.
        
        Args:
            source_doc: Source document
            target_name: Name of target document
            target_doctype: Target DocType
            is_forward: Direction of sync
        """
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
            if not source_rows:
                # If no source rows, delete all target rows
                self._fast_delete_child_rows(target_doctype, target_name, target_table)
                continue
                
            # Get target child table doctype
            try:
                target_meta = frappe.get_meta(target_doctype)
                target_field = target_meta.get_field(target_table)
                if not target_field:
                    continue
                    
                child_doctype = target_field.options
                child_meta = frappe.get_meta(child_doctype)
            except Exception as e:
                frappe.log_error(f"Error getting child table metadata: {str(e)}", "LiveSync Fast Error")
                continue
            
            # Get child table name (tab + DocType)
            child_table = f"tab{child_doctype}"
            
            # Determine key field for matching rows
            key_field = mapping.get("key_field")
            
            # If no key field specified, try to find a suitable one
            if not key_field:
                # Try to find a field that's used for mapping and exists in both source and target
                for src_field, tgt_field in fields.items():
                    if child_meta.has_field(tgt_field):
                        key_field = tgt_field
                        src_key_field = src_field
                        break
                
                # If still no key field, use idx as fallback (position-based matching)
                if not key_field:
                    key_field = "idx"
                    src_key_field = "idx"
            else:
                # Find the source field that maps to key_field
                src_key_field = None
                for s_field, t_field in fields.items():
                    if t_field == key_field:
                        src_key_field = s_field
                        break
                
                # If not found, try reverse mapping
                if not src_key_field:
                    for s_field, t_field in fields.items():
                        if s_field == key_field:
                            src_key_field = s_field
                            break
            
            # Get existing target rows from database
            target_rows = self._fast_get_child_rows(child_table, target_doctype, target_name, target_table)
            
            # Create dictionaries for easier lookup
            source_dict = {}
            for i, row in enumerate(source_rows):
                if src_key_field == "idx":
                    key_value = i+1
                else:
                    key_value = row.get(src_key_field)
                    
                if key_value:
                    source_dict[key_value] = row
            
            target_dict = {}
            for row in target_rows:
                if key_field == "idx":
                    key_value = row.get('idx')
                else:
                    key_value = row.get(key_field)
                    
                if key_value:
                    target_dict[key_value] = row
            
            # Determine rows to update, insert, or delete
            to_update = []
            to_insert = []
            to_delete = []
            
            # Find rows to update or delete
            for tgt_key, tgt_row in target_dict.items():
                if tgt_key in source_dict:
                    # Update existing row
                    src_row = source_dict[tgt_key]
                    
                    # Check if any fields need updating
                    update_fields = []
                    update_values = []
                    
                    for src_field, tgt_field in fields.items():
                        src_value = src_row.get(src_field)
                        current_value = tgt_row.get(tgt_field)
                        
                        # Only update if values differ
                        if src_value != current_value:
                            update_fields.append(tgt_field)
                            update_values.append(src_value)
                    
                    if update_fields:
                        to_update.append({
                            'name': tgt_row.get('name'),
                            'fields': update_fields,
                            'values': update_values
                        })
                else:
                    # Row exists in target but not in source - delete
                    to_delete.append(tgt_row.get('name'))
            
            # Find rows to insert
            for src_key, src_row in source_dict.items():
                if src_key not in target_dict:
                    # New row to insert
                    insert_fields = ['parent', 'parenttype', 'parentfield']
                    insert_values = [target_name, target_doctype, target_table]
                    
                    # Add mapped fields
                    for src_field, tgt_field in fields.items():
                        src_value = src_row.get(src_field)
                        if src_value is not None:
                            insert_fields.append(tgt_field)
                            insert_values.append(src_value)
                    
                    # Add idx field if not mapped
                    if 'idx' not in insert_fields and child_meta.has_field('idx'):
                        idx_value = src_row.get('idx') if hasattr(src_row, 'idx') else len(to_insert) + 1
                        insert_fields.append('idx')
                        insert_values.append(idx_value)
                    
                    # Add standard fields
                    if 'docstatus' not in insert_fields:
                        insert_fields.append('docstatus')
                        insert_values.append(0)
                        
                    if 'owner' not in insert_fields:
                        insert_fields.append('owner')
                        insert_values.append(frappe.session.user)
                        
                    if 'creation' not in insert_fields:
                        insert_fields.append('creation')
                        insert_values.append(frappe.utils.now())
                        
                    if 'modified' not in insert_fields:
                        insert_fields.append('modified')
                        insert_values.append(frappe.utils.now())
                        
                    if 'modified_by' not in insert_fields:
                        insert_fields.append('modified_by')
                        insert_values.append(frappe.session.user)
                    
                    to_insert.append({
                        'fields': insert_fields,
                        'values': insert_values
                    })
            
            # Execute SQL operations
            
            # 1. Delete rows
            if to_delete:
                names_sql = ', '.join(['%s'] * len(to_delete))
                delete_sql = f"DELETE FROM `{child_table}` WHERE name IN ({names_sql})"
                frappe.db.sql(delete_sql, tuple(to_delete))
            
            # 2. Update rows
            for update in to_update:
                if update['fields']:
                    set_clause = ', '.join([f"`{f}` = %s" for f in update['fields']])
                    update_sql = f"UPDATE `{child_table}` SET {set_clause}, `modified` = %s, `modified_by` = %s WHERE name = %s"
                    values = tuple(update['values']) + (frappe.utils.now(), frappe.session.user, update['name'])
                    frappe.db.sql(update_sql, values)
            
            # 3. Insert rows
            for insert in to_insert:
                fields_list = ', '.join([f"`{f}`" for f in insert['fields']])
                values_placeholder = ', '.join(['%s'] * len(insert['fields']))
                insert_sql = f"INSERT INTO `{child_table}` ({fields_list}, `name`) VALUES ({values_placeholder}, %s)"
                
                # Generate a name for the child record
                child_name = frappe.generate_hash(length=10)
                
                values = tuple(insert['values']) + (child_name,)
                frappe.db.sql(insert_sql, values)

        # Commit changes
        frappe.db.commit()

    def _fast_get_child_rows(self, child_table, parent_type, parent_name, parentfield):
        """Get child table rows using direct SQL"""
        sql = f"""
            SELECT * FROM `{child_table}`
            WHERE parenttype = %s AND parent = %s AND parentfield = %s
        """
        return frappe.db.sql(sql, (parent_type, parent_name, parentfield), as_dict=1)

    def _fast_delete_child_rows(self, parent_type, parent_name, parentfield):
        """Delete all child rows for a parent using direct SQL"""
        # Get the child doctype from parentfield
        try:
            parent_meta = frappe.get_meta(parent_type)
            child_doctype = parent_meta.get_field(parentfield).options
            child_table = f"tab{child_doctype}"
            
            sql = f"""
                DELETE FROM `{child_table}`
                WHERE parenttype = %s AND parent = %s AND parentfield = %s
            """
            frappe.db.sql(sql, (parent_type, parent_name, parentfield))
        except Exception as e:
            frappe.log_error(f"Error deleting child rows: {str(e)}", "LiveSync Fast Error")

    def _fast_process_field_mappings(self, source_doc, target_doctype, target_name, is_forward=True):
        """
        Process field mappings using direct SQL in fast mode
        Returns fields and values for parent document update
        """
        # Get field mappings based on direction
        field_mappings = self.config.get("direct_fields", {})
        if not is_forward:
            field_mappings = {v: k for k, v in field_mappings.items()}
        
        # Categorize field mappings
        standard_fields = []  # Fields to update on parent
        standard_values = []  # Values to update on parent
        parent_to_child = {}  # Parent to child mappings
        child_to_parent = {}  # Child to parent mappings
        
        # Categorize each mapping
        for src_field, tgt_field in field_mappings.items():
            src_is_child = "." in src_field
            tgt_is_child = "." in tgt_field
            
            if not src_is_child and not tgt_is_child:
                # Standard field mapping (parent to parent)
                src_value = source_doc.get(src_field)
                if src_value is not None:
                    # Apply transformation if configured
                    transform_config = self.config.get("transform", {})
                    if src_field in transform_config:
                        try:
                            transform_name = transform_config[src_field]
                            transform_function = frappe.get_attr(transform_name)
                            src_value = transform_function(src_value, source_doc)
                        except Exception as e:
                            frappe.log_error(f"Error applying transform: {str(e)}", "Fast Sync Error")
                    
                    standard_fields.append(tgt_field)
                    standard_values.append(src_value)
            elif src_is_child and not tgt_is_child:
                # Child to parent mapping
                child_to_parent[src_field] = tgt_field
            elif not src_is_child and tgt_is_child:
                # Parent to child mapping
                parent_to_child[src_field] = tgt_field
        
        # Process child to parent mappings
        if child_to_parent:
            for src_field, tgt_field in child_to_parent.items():
                value = self._fast_get_child_field_value(source_doc, src_field)
                if value is not None:
                    # Apply transformation if configured
                    transform_config = self.config.get("transform", {})
                    if src_field in transform_config:
                        try:
                            transform_name = transform_config[src_field]
                            transform_function = frappe.get_attr(transform_name)
                            value = transform_function(value, source_doc)
                        except Exception as e:
                            frappe.log_error(f"Error applying transform: {str(e)}", "Fast Sync Error")
                            
                    standard_fields.append(tgt_field)
                    standard_values.append(value)
        
        # Return parent fields and values for SQL UPDATE
        return standard_fields, standard_values, parent_to_child

    def _fast_get_child_field_value(self, doc, field_path):
        """Get value from child table field using parsing"""
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
            # Default to first row
            return child_table[0].get(field_name) if child_table else None
            
        return None

    def _fast_process_parent_to_child(self, source_doc, target_doctype, target_name, parent_to_child, is_forward=True):
        """Process parent to child mappings using direct SQL"""
        if not parent_to_child:
            return
            
        for src_field, tgt_field in parent_to_child.items():
            # Get source value
            src_value = source_doc.get(src_field)
            if src_value is None:
                continue
                
            # Apply transformation if configured
            transform_config = self.config.get("transform", {})
            if src_field in transform_config:
                try:
                    transform_name = transform_config[src_field]
                    transform_function = frappe.get_attr(transform_name)
                    src_value = transform_function(src_value, source_doc)
                except Exception as e:
                    frappe.log_error(f"Error applying transform: {str(e)}", "Fast Sync Error")
                    continue
                    
            # Parse target field
            path_info = self._parse_table_reference(tgt_field)
            table_name = path_info["table"]
            field_name = path_info["field"]
            index = path_info["index"]
            
            # Get child table doctype
            try:
                parent_meta = frappe.get_meta(target_doctype)
                child_doctype = parent_meta.get_field(table_name).options
                child_table = f"tab{child_doctype}"
            except Exception as e:
                frappe.log_error(f"Error getting child doctype: {str(e)}", "Fast Sync Error")
                continue
            
            if index is not None:
                # Specific index requested
                self._fast_update_child_at_index(child_table, target_doctype, target_name, 
                                                table_name, index, field_name, src_value)
            else:
                # First row or create new
                self._fast_update_first_child_row(child_table, target_doctype, target_name, 
                                                table_name, field_name, src_value, child_doctype)

    def _fast_update_child_at_index(self, child_table, parent_type, parent_name, 
                                parentfield, index, field_name, value):
        """Update child row at specific index"""
        # Get existing rows
        rows = self._fast_get_child_rows(child_table, parent_type, parent_name, parentfield)
        
        if len(rows) > index:
            # Update existing row
            row = rows[index]
            if row.get(field_name) != value:
                update_sql = f"""
                    UPDATE `{child_table}` 
                    SET `{field_name}` = %s, `modified` = %s, `modified_by` = %s
                    WHERE name = %s
                """
                frappe.db.sql(update_sql, (value, frappe.utils.now(), frappe.session.user, row.name))
        else:
            # Need to create new rows up to index
            meta = frappe.get_meta(parent_type)
            child_doctype = meta.get_field(parentfield).options
            
            # Get current row count
            current_count = len(rows)
            
            # Create rows until we reach the desired index
            for i in range(current_count, index + 1):
                # Generate a unique name for child doc
                child_name = frappe.generate_hash(length=10)
                
                # Define fields for new row
                fields = ['name', 'parent', 'parenttype', 'parentfield', 'idx', 'owner', 
                        'creation', 'modified', 'modified_by', 'docstatus']
                
                # Set values
                values = [
                    child_name, 
                    parent_name,
                    parent_type,
                    parentfield,
                    i + 1,  # idx is 1-based
                    frappe.session.user,
                    frappe.utils.now(),
                    frappe.utils.now(),
                    frappe.session.user,
                    0
                ]
                
                # Add the field to update if this is the target index
                if i == index:
                    fields.append(field_name)
                    values.append(value)
                
                # Create INSERT SQL
                fields_str = ', '.join([f"`{f}`" for f in fields])
                placeholders = ', '.join(['%s'] * len(fields))
                insert_sql = f"INSERT INTO `{child_table}` ({fields_str}) VALUES ({placeholders})"
                
                # Execute SQL
                frappe.db.sql(insert_sql, tuple(values))

    def _fast_update_first_child_row(self, child_table, parent_type, parent_name, 
                                parentfield, field_name, value, child_doctype):
        """Update the first row of a child table or create if none exists"""
        # Check if any rows exist
        rows = self._fast_get_child_rows(child_table, parent_type, parent_name, parentfield)
        
        if rows:
            # Update the first row
            row = rows[0]
            if row.get(field_name) != value:
                update_sql = f"""
                    UPDATE `{child_table}` 
                    SET `{field_name}` = %s, `modified` = %s, `modified_by` = %s
                    WHERE name = %s
                """
                frappe.db.sql(update_sql, (value, frappe.utils.now(), frappe.session.user, row.name))
        else:
            # Create a new row
            child_name = frappe.generate_hash(length=10)
            
            # Define fields
            fields = ['name', 'parent', 'parenttype', 'parentfield', 'idx', field_name,
                    'owner', 'creation', 'modified', 'modified_by', 'docstatus']
            
            # Set values
            values = [
                child_name,
                parent_name,
                parent_type,
                parentfield,
                1,  # idx is 1-based
                value,
                frappe.session.user,
                frappe.utils.now(),
                frappe.utils.now(),
                frappe.session.user,
                0
            ]
            
            # Create INSERT SQL
            fields_str = ', '.join([f"`{f}`" for f in fields])
            placeholders = ', '.join(['%s'] * len(fields))
            insert_sql = f"INSERT INTO `{child_table}` ({fields_str}) VALUES ({placeholders})"
            
            # Execute SQL
            frappe.db.sql(insert_sql, tuple(values))
            
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
        """
        Process all field mappings with optimization for standard fields.
        Handles parent-child and child-parent mappings efficiently.
        Only updates fields that have changed.
        """
        # Categorize field mappings
        standard_mappings = {}  # parent to parent
        parent_to_child = {}    # parent to child
        child_to_parent = {}    # child to parent
        child_to_child = {}     # child to child (handled separately in _process_child_tables)
        
        # Get mappings from configuration
        field_mappings = self.config.get("direct_fields", {})
        
        # Reverse mappings if needed
        if not is_forward:
            field_mappings = {v: k for k, v in field_mappings.items()}
        
        # Categorize each mapping
        for src_field, tgt_field in field_mappings.items():
            src_is_child = "." in src_field
            tgt_is_child = "." in tgt_field
            
            if not src_is_child and not tgt_is_child:
                # Standard field mapping (parent to parent)
                standard_mappings[src_field] = tgt_field
            elif src_is_child and not tgt_is_child:
                # Child to parent mapping
                child_to_parent[src_field] = tgt_field
            elif not src_is_child and tgt_is_child:
                # Parent to child mapping
                parent_to_child[src_field] = tgt_field
            # child to child handled in _process_child_tables
        
        # 1. Process standard field mappings (more efficient batch update)
        self._process_standard_field_mappings(source_doc, target_doc, standard_mappings)
        
        # 2. Process child to parent mappings
        for src_field, tgt_field in child_to_parent.items():
            self._map_child_to_parent_field(source_doc, target_doc, src_field, tgt_field)
        
        # 3. Process parent to child mappings
        for src_field, tgt_field in parent_to_child.items():
            self._map_parent_to_child_field(source_doc, target_doc, src_field, tgt_field)
            
    def _process_standard_field_mappings(self, source_doc, target_doc, field_mappings):
        """Process standard (non-hierarchical) field mappings efficiently"""
        # Only update fields that have changed
        for src_field, tgt_field in field_mappings.items():
            src_value = source_doc.get(src_field)
            curr_value = target_doc.get(tgt_field)
            
            # Only set if values are different to avoid unnecessary updates
            if src_value != curr_value and src_value is not None:
                # Apply transformation if configured
                transform_config = self.config.get("transform", {})
                if src_field in transform_config:
                    src_value = self._apply_transform(src_field, src_value, source_doc)
                
                target_doc.set(tgt_field, src_value)

    def _map_child_to_parent_field(self, source_doc, target_doc, src_field, tgt_field):
        """Map field from child table to parent document"""
        # Parse the source field path to get table, field and index
        path_info = self._parse_table_reference(src_field)
        table_name = path_info["table"]
        field_name = path_info["field"]
        index = path_info["index"]
        
        # Get the value from the child table
        value = None
        child_table = source_doc.get(table_name, [])
        
        if child_table:
            if index is not None:
                # Specific index
                if len(child_table) > index:
                    row = child_table[index]
                    value = row.get(field_name)
            else:
                # Default to first row
                row = child_table[0]
                value = row.get(field_name) if row else None
        
        # Only update if value exists and differs from current
        if value is not None and value != target_doc.get(tgt_field):
            # Apply transformation if configured
            transform_config = self.config.get("transform", {})
            if src_field in transform_config:
                value = self._apply_transform(src_field, value, source_doc)
                
            target_doc.set(tgt_field, value)

    def _map_parent_to_child_field(self, source_doc, target_doc, src_field, tgt_field):
        """Map field from parent document to child table field"""
        # Get source value from parent
        src_value = source_doc.get(src_field)
        if src_value is None:
            return  # No value to set
        
        # Apply transformation if configured
        transform_config = self.config.get("transform", {})
        if src_field in transform_config:
            src_value = self._apply_transform(src_field, src_value, source_doc)
        
        # Parse the target field path
        path_info = self._parse_table_reference(tgt_field)
        table_name = path_info["table"]
        field_name = path_info["field"]
        index = path_info["index"]
        
        # Get or create the child table in target
        child_table = target_doc.get(table_name, [])
        
        # Get child table doctype
        meta = frappe.get_meta(target_doc.doctype)
        table_field = meta.get_field(table_name)
        if not table_field:
            return  # Table doesn't exist
            
        child_doctype = table_field.options
        
        # Handle based on index
        if index is not None:
            # Ensure child table has enough rows
            while len(child_table) <= index:
                new_row = frappe.new_doc(child_doctype)
                new_row.parentfield = table_name
                child_table.append(new_row)
                
            # Set the value in the specified row
            row = child_table[index]
            if row.get(field_name) != src_value:  # Only update if changed
                row.set(field_name, src_value)
        else:
            # No index specified, use first row or create one
            if not child_table:
                new_row = frappe.new_doc(child_doctype)
                new_row.parentfield = table_name
                new_row.set(field_name, src_value)
                child_table.append(new_row)
            else:
                # Update first row if value differs
                row = child_table[0]
                if row.get(field_name) != src_value:
                    row.set(field_name, src_value)
        
        # Update the table in the target doc
        target_doc.set(table_name, child_table)
    
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