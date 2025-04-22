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
        
        // // Add "View Configuration Guide" button
        // frm.add_custom_button(__('View Configuration Guide'), function() {
        //     show_config_guide();
        // }, __('Help'));
        
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
                method: 'core.agnikul_core_erp.doctype.live_sync.live_sync.run_test_sync',
                args: {
                    doctype: frm.doctype,
                    docname: frm.docname,
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
                    doc: frm.doc,
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
                                message: r.message ? r.message.message : __('An error occurred during sync')
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

// // Function to show configuration guide in a dialog
// function show_config_guide() {
//     var d = new frappe.ui.Dialog({
//         title: __('Configuration Guide'),
//         size: 'large', // Use a large dialog
//         fields: [{
//             fieldtype: 'HTML',
//             fieldname: 'config_guide',
//             options: `
//                 <div style="height: 400px; overflow-y: auto; padding-right: 10px;">
//                     <h4>Configuration Structure</h4>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px; overflow-x: auto;">
// {
//   "direct_fields": {
//     "source_field1": "target_field1",
//     "source_field2": "target_field2"
//   },
//   "child_mappings": [
//     {
//       "source_table": "source_child_table",
//       "target_table": "target_child_table",
//       "fields": {
//         "source_field1": "target_field1",
//         "source_field2": "target_field2"
//       },
//       "key_field": "id_field"
//     }
//   ],
//   "conditions": {
//     "only_if": [
//       ["status", "==", "Active"]
//     ],
//     "skip_if": [
//       ["is_cancelled", "==", true]
//     ]
//   },
//   "transform": {
//     "field_name": "function_name"
//   },
//   "hooks": {
//     "before_sync": "module.function_name",
//     "after_sync": "module.function_name"
//   },
//   "options": {
//     "sync_attachments": true,
//     "sync_comments": false
//   }
// }</pre>
                    
//                     <h4>1. Direct Fields Mapping</h4>
//                     <p>Map fields directly from source to target document:</p>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px;">
// "direct_fields": {
//   "employee_id": "user_id",
//   "employee_name": "full_name",
//   "department": "department"
// }</pre>
                    
//                     <h4>2. Child Table Mapping</h4>
//                     <p>Map child tables between documents:</p>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px;">
// "child_mappings": [
//   {
//     "source_table": "education",
//     "target_table": "qualifications",
//     "fields": {
//       "degree": "qualification",
//       "institution": "school",
//       "year": "completion_year"
//     },
//     "key_field": "degree"
//   }
// ]</pre>
//                     <p><strong>Note:</strong> Use field names (e.g., "education"), not DocType names (e.g., "Education Detail")</p>
                    
//                     <h4>3. Conditions</h4>
//                     <p>Control when syncing should occur:</p>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px;">
// "conditions": {
//   "only_if": [
//     ["status", "==", "Active"],
//     ["department", "in", ["IT", "HR", "Finance"]]
//   ],
//   "skip_if": [
//     ["is_temporary", "==", true]
//   ]
// }</pre>
//                     <p><strong>Supported operators:</strong> ==, !=, >, <, >=, <=, in, not in, contains, starts with, ends with</p>
                    
//                     <h4>4. Field Transformations</h4>
//                     <p>Apply custom functions to transform field values:</p>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px;">
// "transform": {
//   "salary": "your_app_name.live_sync_hooks.convert_to_annual",
//   "joining_date": "your_app_name.live_sync_hooks.format_date"
// }</pre>
//                     <p>Each function should accept (value, doc) parameters and return the transformed value.</p>
                    
//                     <h4>5. Sync Hooks</h4>
//                     <p>Execute custom code before or after sync:</p>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px;">
// "hooks": {
//   "before_sync": "your_app_name.live_sync_hooks.before_sync_employee",
//   "after_sync": "your_app_name.live_sync_hooks.after_sync_employee"
// }</pre>
//                     <p>Hook functions receive parameters:</p>
//                     <ul>
//                         <li><strong>before_sync:</strong> (source_doc, is_forward, sync_config)</li>
//                         <li><strong>after_sync:</strong> (source_doc, target_doc, is_forward, sync_config)</li>
//                     </ul>
                    
//                     <h4>6. Additional Options</h4>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px;">
// "options": {
//   "sync_attachments": true,
//   "sync_comments": false,
//   "update_modified": false
// }</pre>
                    
//                     <h4>Example: Complete Configuration</h4>
//                     <pre style="background-color: #f8f8f8; padding: 10px; border-radius: 4px; overflow-x: auto;">
// {
//   "direct_fields": {
//     "employee_id": "user_id",
//     "employee_name": "full_name",
//     "department": "department",
//     "joining_date": "start_date",
//     "salary": "compensation"
//   },
//   "child_mappings": [
//     {
//       "source_table": "education",
//       "target_table": "qualifications",
//       "fields": {
//         "degree": "qualification",
//         "institution": "school",
//         "year": "completion_year"
//       },
//       "key_field": "degree"
//     }
//   ],
//   "conditions": {
//     "only_if": [
//       ["status", "==", "Active"]
//     ],
//     "skip_if": [
//       ["is_temporary", "==", true]
//     ]
//   },
//   "transform": {
//     "salary": "your_app_name.live_sync_hooks.convert_to_annual",
//     "joining_date": "your_app_name.live_sync_hooks.format_date"
//   },
//   "hooks": {
//     "before_sync": "your_app_name.live_sync_hooks.before_sync_employee",
//     "after_sync": "your_app_name.live_sync_hooks.after_sync_employee"
//   },
//   "options": {
//     "sync_attachments": true
//   }
// }</pre>
//                 </div>
//             `
//         }]
//     });
    
//     d.show();
// }