import frappe

############# Name Sync Hooks #############
def sync_name(source_doc, target_doc, is_forward, sync_config):
    """
    Sets the name of the target document without inserting it.
    
    This is a lightweight sync_name hook that only sets the name
    and lets the main sync process handle field mappings and insertion.
    """
    target_doctype = sync_config.target_doctype if is_forward else sync_config.source_doctype
    source_name = source_doc.name
    
    # If the target record already exists by name, load and return it
    if frappe.db.exists(target_doctype, source_name):
        return frappe.get_doc(target_doctype, source_name)

    # Create a new document with the correct name
    new_doc = frappe.new_doc(target_doctype)
    
    # Set the name to match source document
    new_doc.name = source_name
    
    # Don't insert yet - let the main sync flow handle the insert
    # with all the field mappings applied
    return new_doc

def set_name(source_doc, target_doc, is_forward, sync_config):
    """
    Creates and inserts a new document with the same name as the source.
    
    This hook creates, populates, and inserts the target document into the database.
    Use this when you need custom field processing before the document is inserted.
    """
    target_doctype = sync_config.target_doctype if is_forward else sync_config.source_doctype
    source_name = source_doc.name

    # If the target record already exists by name, load and return it
    if frappe.db.exists(target_doctype, source_name):
        return frappe.get_doc(target_doctype, source_name)

    # Create a new document
    new_doc = frappe.new_doc(target_doctype)
    
    # Set the name
    new_doc.name = source_name
    
    # Insert the document
    new_doc.insert(ignore_permissions=True)
    
    return new_doc

############# Before Sync Hooks #############


############# After Sync Hooks #############
# def sync_name(source_doc, target_doc, is_forward, sync_config):
#     target_doctype = sync_config.target_doctype if is_forward else sync_config.source_doctype
#     source_name = source_doc.name

#     # 1) If the target record already exists by name, load and return it
#     if frappe.db.exists(target_doctype, source_name):
#         return frappe.get_doc(target_doctype, source_name)

#     # 2) Otherwise, create a fresh one
#     new_doc = frappe.new_doc(target_doctype)
#     new_doc.update(target_doc.as_dict())

#     # Clean system fields
#     for f in ("creation","modified","modified_by","owner","idx"):
#         new_doc.pop(f, None)

#     # Set the correct name
#     new_doc.name = source_name

#     # Because your Doctype is Set By User, .insert() will trust this name
#     new_doc.insert(ignore_permissions=True)

#     frappe.log_error(
#         f"Created new {target_doctype} named {source_name}",
#         "LiveSync Name Hook"
#     )

#     return new_doc