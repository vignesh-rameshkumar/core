// Copyright (c) 2025, Agnikul Cosmos Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Live Sync', {
    refresh: function(frm) {
        // Add buttons to test and run sync operations
        frm.add_custom_button(__('Test Sync'), function() {
            // Show dialog to select document
            frappe.prompt([
                {
                    fieldname: 'doctype',
                    label: __('DocType'),
                    fieldtype: 'Select',
                    options: [frm.doc.source_doctype, frm.doc.target_doctype],
                    default: frm.doc.source_doctype,
                    reqd: 1
                },
                {
                    fieldname: 'docname',
                    label: __('Document Name'),
                    fieldtype: 'Data',
                    reqd: 1,
                    description: __('Leave empty for random document')
                }
            ], function(values) {
                frm.call({
                    method: 'test_sync',
                    args: {
                        source_doctype: values.doctype,
                        source_name: values.docname || null
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            // Show test results in dialog
                            show_test_results(r.message);
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message ? r.message.message : __('Unknown error occurred')
                            });
                        }
                    }
                });
            }, __('Test Sync'));
        }, __('Actions'));
        
        frm.add_custom_button(__('Run Sync'), function() {
            // Show dialog to select document
            frappe.prompt([
                {
                    fieldname: 'doctype',
                    label: __('DocType'),
                    fieldtype: 'Select',
                    options: [frm.doc.source_doctype, frm.doc.target_doctype],
                    default: frm.doc.source_doctype,
                    reqd: 1
                },
                {
                    fieldname: 'docname',
                    label: __('Document Name'),
                    fieldtype: 'Data',
                    reqd: 1
                }
            ], function(values) {
                frm.call({
                    method: 'run_sync_for_document',
                    args: {
                        source_doctype: values.doctype,
                        source_name: values.docname
                    },
                    freeze: true,
                    freeze_message: __('Running Sync...'),
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: r.message.message
                            });
                            
                            // If a document was created, open it
                            if (r.message.target_name) {
                                frappe.set_route('Form', r.message.target_doctype, r.message.target_name);
                            }
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message ? r.message.message : __('Unknown error occurred')
                            });
                        }
                    }
                });
            }, __('Run Sync'));
        }, __('Actions'));
        
        // Add button to sync all documents
        frm.add_custom_button(__('Sync All Documents'), function() {
            frappe.confirm(
                __('This will attempt to sync all documents from {0}. This operation can be resource-intensive. Continue?', [frm.doc.source_doctype]),
                function() {
                    frm.call({
                        method: 'sync_all_documents',
                        freeze: true,
                        freeze_message: __('Syncing Documents...'),
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint({
                                    title: __('Sync Completed'),
                                    indicator: 'green',
                                    message: r.message.message
                                });
                            } else {
                                frappe.msgprint({
                                    title: __('Error'),
                                    indicator: 'red',
                                    message: r.message ? r.message.message : __('Unknown error occurred')
                                });
                            }
                        }
                    });
                }
            );
        }, __('Actions'));
        
        // Add button to view logs
        frm.add_custom_button(__('View Logs'), function() {
            frappe.set_route('List', 'Sync Log', {sync_configuration: frm.doc.name});
        }, __('Actions'));
        
        // Helper to show test results
        function show_test_results(data) {
            // Create HTML for field mappings
            let field_mappings_html = '';
            if (data.field_mappings && data.field_mappings.length > 0) {
                field_mappings_html = '<h5>' + __('Field Mappings') + '</h5>' +
                    '<table class="table table-bordered">' +
                    '<thead><tr>' +
                    '<th>' + __('Source Field') + '</th>' +
                    '<th>' + __('Target Field') + '</th>' +
                    '<th>' + __('Original Value') + '</th>' +
                    '<th>' + __('Mapped Value') + '</th>' +
                    '</tr></thead><tbody>';
                
                data.field_mappings.forEach(function(mapping) {
                    field_mappings_html += '<tr>' +
                        '<td>' + mapping.source_field + '</td>' +
                        '<td>' + mapping.target_field + '</td>' +
                        '<td>' + (mapping.original_value !== null ? mapping.original_value : '') + '</td>' +
                        '<td>' + (mapping.mapped_value !== null ? mapping.mapped_value : '') + '</td>' +
                        '</tr>';
                });
                
                field_mappings_html += '</tbody></table>';
            }
            
            // Create HTML for child table mappings
            let child_mappings_html = '';
            if (data.child_mappings && data.child_mappings.length > 0) {
                child_mappings_html = '<h5>' + __('Child Table Mappings') + '</h5>' +
                    '<table class="table table-bordered">' +
                    '<thead><tr>' +
                    '<th>' + __('Source Table') + '</th>' +
                    '<th>' + __('Target Table') + '</th>' +
                    '<th>' + __('Rows') + '</th>' +
                    '</tr></thead><tbody>';
                
                data.child_mappings.forEach(function(mapping) {
                    child_mappings_html += '<tr>' +
                        '<td>' + mapping.source_table + '</td>' +
                        '<td>' + mapping.target_table + '</td>' +
                        '<td>' + mapping.source_count + ' → ' + mapping.target_count + '</td>' +
                        '</tr>';
                });
                
                child_mappings_html += '</tbody></table>';
            }
            
            // Create HTML for conditions
            let conditions_html = '<div class="alert alert-' + (data.conditions_met ? 'success' : 'warning') + '">' +
                '<i class="fa fa-' + (data.conditions_met ? 'check-circle' : 'exclamation-triangle') + '"></i> ' +
                __('Conditions: ') + (data.conditions_met ? 
                    __('All conditions are met - sync would proceed') : 
                    __('Conditions not met - sync would be skipped')) +
                '</div>';
            
            // Show results in dialog
            let d = new frappe.ui.Dialog({
                title: __('Test Sync Results'),
                fields: [{
                    fieldtype: 'HTML',
                    fieldname: 'results',
                    options: '<div>' +
                        '<p><strong>' + __('Source Document:') + '</strong> ' + data.source_doc + '</p>' +
                        conditions_html +
                        field_mappings_html +
                        child_mappings_html +
                        '</div>'
                }],
                primary_action_label: __('Close'),
                primary_action: function() {
                    d.hide();
                }
            });
            
            d.show();
        }
    },
    
    source_doctype: function(frm) {
        // Refresh field options when source doctype changes
        frm.trigger('refresh_field_options');
    },
    
    target_doctype: function(frm) {
        // Refresh field options when target doctype changes
        frm.trigger('refresh_field_options');
    },
    
    refresh_field_options: function(frm) {
        // Get fields from selected doctypes
        if (frm.doc.source_doctype && frm.doc.target_doctype) {
            frm.call({
                method: 'frappe.client.get_meta',
                args: {
                    doctype: frm.doc.source_doctype
                },
                callback: function(r) {
                    if (r.message) {
                        frm.source_fields = r.message.fields;
                        frm.trigger('update_field_options');
                    }
                }
            });
            
            frm.call({
                method: 'frappe.client.get_meta',
                args: {
                    doctype: frm.doc.target_doctype
                },
                callback: function(r) {
                    if (r.message) {
                        frm.target_fields = r.message.fields;
                        frm.trigger('update_field_options');
                    }
                }
            });
        }
    },
    
    update_field_options: function(frm) {
        // Update field mapping options when both doctypes are loaded
        if (frm.source_fields && frm.target_fields) {
            // Get field names and labels
            let source_options = [];
            let target_options = [];
            
            frm.source_fields.forEach(function(f) {
                if (!['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button'].includes(f.fieldtype)) {
                    source_options.push({
                        value: f.fieldname,
                        label: `${f.label || f.fieldname} (${f.fieldtype})`
                    });
                }
            });
            
            frm.target_fields.forEach(function(f) {
                if (!['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button'].includes(f.fieldtype)) {
                    target_options.push({
                        value: f.fieldname,
                        label: `${f.label || f.fieldname} (${f.fieldtype})`
                    });
                }
            });
            
            // Set options in the field mappings table
            frm.set_df_property('field_mappings', 'fields', [
                {
                    fieldname: 'source_field',
                    fieldtype: 'Autocomplete',
                    label: 'Source Field',
                    options: source_options,
                    reqd: 1
                },
                {
                    fieldname: 'target_field',
                    fieldtype: 'Autocomplete',
                    label: 'Target Field',
                    options: target_options,
                    reqd: 1
                },
                {
                    fieldname: 'transformation',
                    fieldtype: 'Code',
                    label: 'Transformation',
                    options: 'Python'
                }
            ]);
            
            // Refresh the field to show the new options
            frm.refresh_field('field_mappings');
        }
    }
});