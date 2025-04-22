// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('Live Sync', {
    refresh: function(frm) {
        // Set up help text for configuration
        if (!frm.doc.config || frm.doc.config === '{}') {
            frm.set_value('config', JSON.stringify({
                "direct_fields": {},
                "child_mappings": []
            }, null, 4));
        }
        
        // Add configuration help
        frm.set_df_property('config', 'description', 
            `<div class="text-muted">
                <p><strong>Example configuration:</strong></p>
                <pre>{
  "direct_fields": {
    "source_field1": "target_field1",
    "source_field2": "target_field2"
  },
  "child_mappings": [
    {
      "source_table": "source_child_table",
      "source_field": "source_field",
      "target_table": "target_child_table",
      "target_field": "target_field"
    }
  ]
}</pre>
            </div>`
        );
        
        // Add test sync button
        frm.add_custom_button(__('Test Sync'), function() {
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
                    method: 'test_sync',
                    args: {
                        source_doctype: values.doctype,
                        source_name: values.docname
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            // Show test results
                            var html = '<div>';
                            html += '<p><strong>' + __('Source Document') + ':</strong> ' + r.message.source_doc + '</p>';
                            
                            if (r.message.target_exists) {
                                html += '<p><strong>' + __('Target Document') + ':</strong> ' + r.message.target_doc + '</p>';
                                html += '<p class="text-success"><i class="fa fa-check"></i> ' + __('Target document exists, it would be updated') + '</p>';
                            } else {
                                html += '<p class="text-warning"><i class="fa fa-info-circle"></i> ' + __('No target document found, a new one would be created') + '</p>';
                            }
                            
                            html += '<h5>' + __('Field Mappings') + '</h5>';
                            html += '<table class="table table-bordered">';
                            html += '<thead><tr><th>' + __('Source Field') + '</th><th>' + __('Target Field') + '</th><th>' + __('Value') + '</th></tr></thead>';
                            html += '<tbody>';
                            
                            r.message.field_mappings.forEach(function(mapping) {
                                html += '<tr>';
                                html += '<td>' + mapping.source_field + '</td>';
                                html += '<td>' + mapping.target_field + '</td>';
                                html += '<td>' + (mapping.value !== null && mapping.value !== undefined ? mapping.value : '') + '</td>';
                                html += '</tr>';
                            });
                            
                            html += '</tbody></table>';
                            html += '</div>';
                            
                            var d = new frappe.ui.Dialog({
                                title: __('Test Sync Results'),
                                fields: [{
                                    fieldtype: 'HTML',
                                    fieldname: 'results',
                                    options: html
                                }]
                            });
                            
                            d.show();
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message.message || __('An error occurred during test')
                            });
                        }
                    }
                });
            }, __('Test Sync'), __('Test'));
        }, __('Actions'));
        
        // Add trigger sync button
        frm.add_custom_button(__('Trigger Sync'), function() {
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
                    method: 'trigger_sync_for_document',
                    args: {
                        doctype: values.doctype,
                        docname: values.docname
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: r.message.message
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message.message || __('An error occurred during sync')
                            });
                        }
                    }
                });
            }, __('Trigger Sync'), __('Sync'));
        }, __('Actions'));
        
        // Add view logs button
        frm.add_custom_button(__('View Logs'), function() {
            frappe.set_route('List', 'Sync Log', {sync_configuration: frm.doc.name});
        }, __('Actions'));
    },
    
    validate: function(frm) {
        // Validate configuration is valid JSON
        try {
            if (frm.doc.config) {
                JSON.parse(frm.doc.config);
            }
        } catch (e) {
            frappe.msgprint({
                title: __('Invalid JSON'),
                indicator: 'red',
                message: __('Configuration must be valid JSON. Error: ') + e.message
            });
            frappe.validated = false;
        }
    }
});