import frappe

############# Before Sync Hooks #############


############# After Sync Hooks #############
def sync_name(source_doc, target_doc, is_forward, sync_config):

    # Determine if we need to rename
    if is_forward:
        # Target document should get source document's name
        new_name = source_doc.name
        doc_to_rename = target_doc
    else:
        # First, find the matching source document
        source_doctype = sync_config.source_doctype
        filters = {}
        
        # Use identifier mapping to find the matching document
        identifier_mapping = sync_config.config.get("identifier_mapping", {})
        if identifier_mapping:
            for src_field, tgt_field in identifier_mapping.items():
                if hasattr(source_doc, tgt_field):
                    value = source_doc.get(tgt_field)
                    filters[src_field] = value
                    break
        
        # If no identifier mapping or couldn't find value, try the first field mapping
        if not filters and sync_config.config.get("direct_fields"):
            field_mappings = sync_config.config.get("direct_fields", {})
            for src_field, tgt_field in field_mappings.items():
                if hasattr(source_doc, tgt_field):
                    value = source_doc.get(tgt_field)
                    filters[src_field] = value
                    break
                    
        # If we still don't have filters, we can't find the matching source doc
        if not filters:
            frappe.log_error(
                f"Could not determine filters to find source document for {source_doc.doctype} {source_doc.name}",
                "Document Name Sync Error"
            )
            return
            
        # Find the matching source document
        source_docs = frappe.get_all(
            source_doctype,
            filters=filters,
            fields=["name"],
            limit=1
        )
        
        if not source_docs:
            frappe.log_error(
                f"Could not find matching source document for {source_doc.doctype} {source_doc.name} with filters {filters}",
                "Document Name Sync Error"
            )
            return
            
        # Use the source document's name
        new_name = source_docs[0].name
        doc_to_rename = target_doc
        
    # If the document already has the correct name, don't do anything
    if doc_to_rename.name == new_name:
        return
        
    try:
        # Rename the document
        frappe.rename_doc(
            doc_to_rename.doctype,
            doc_to_rename.name,
            new_name,
            force=True
        )
        
        frappe.log_error(
            f"Renamed {doc_to_rename.doctype} from {doc_to_rename.name} to {new_name}. "
            f"Direction: {'Forward' if is_forward else 'Backward'}",
            "Document Name Sync"
        )
    except Exception as e:
        frappe.log_error(
            f"Error renaming document {doc_to_rename.doctype} {doc_to_rename.name} to {new_name}: {str(e)}",
            "Document Name Sync Error"
        )