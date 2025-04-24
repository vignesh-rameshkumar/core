// Copyright (c) 2025, Agnikul Cosmos and contributors
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
                    doc: frm.doc,
                    args: {
                        source_doctype: values.doctype,
                        source_name: values.docname
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            // Build a comprehensive HTML report
                            var html = '<div class="sync-preview" style="color: var(--text-color);">';
                            
                            // Basic info
                            html += '<div class="row">';
                            html += '<div class="col-md-6">';
                            html += '<p><strong>' + __('Source') + ':</strong> ' + r.message.source_doctype + ' - ' + r.message.source_doc + '</p>';
                            html += '</div>';
                            html += '<div class="col-md-6">';
                            if (r.message.target_exists) {
                                html += '<p><strong>' + __('Target') + ':</strong> ' + r.message.target_doctype + ' - ' + r.message.target_doc + '</p>';
                                html += '<p style="color: var(--success-color);"><i class="fa fa-check"></i> ' + __('Target document exists, it would be updated') + '</p>';
                            } else {
                                html += '<p><strong>' + __('Target') + ':</strong> ' + r.message.target_doctype + ' - ' + __('New document would be created') + '</p>';
                                html += '<p style="color: var(--warning-color);"><i class="fa fa-info-circle"></i> ' + __('No target document found, a new one would be created') + '</p>';
                            }
                            html += '</div>';
                            html += '</div>';
                            
                            html += '<hr>';
                            
                            // Direct field mappings
                            html += '<h5>' + __('Field Mappings') + '</h5>';
                            html += '<table class="table table-bordered" style="color: var(--text-color); background: var(--card-bg);">';
                            html += '<thead style="background: var(--control-bg);"><tr>';
                            html += '<th>' + __('Source Field') + '</th>';
                            html += '<th>' + __('Target Field') + '</th>';
                            html += '<th>' + __('Value') + '</th>';
                            html += '<th>' + __('Transformation') + '</th>';
                            html += '</tr></thead>';
                            html += '<tbody>';
                            
                            r.message.field_mappings.forEach(function(mapping) {
                                html += '<tr>';
                                html += '<td>' + mapping.source_field + '</td>';
                                html += '<td>' + mapping.target_field + '</td>';
                                html += '<td>' + (mapping.value !== null && mapping.value !== undefined ? mapping.value : '') + '</td>';
                                html += '<td>' + (mapping.transform || '') + '</td>';
                                html += '</tr>';
                            });
                            
                            html += '</tbody></table>';
                            
                            // Child table mappings
                            if (r.message.child_mappings && r.message.child_mappings.length > 0) {
                                html += '<h5>' + __('Child Table Mappings') + '</h5>';
                                
                                r.message.child_mappings.forEach(function(mapping, index) {
                                    html += '<div class="card mb-3" style="background: var(--card-bg); border-color: var(--border-color);">';
                                    html += '<div class="card-header" style="background: var(--control-bg); color: var(--text-color);">';
                                    html += '<strong>' + mapping.source_table + '</strong> → <strong>' + mapping.target_table + '</strong>';
                                    html += ' (' + mapping.row_count + ' ' + (mapping.row_count === 1 ? __('row') : __('rows')) + ')';
                                    html += '</div>';
                                    html += '<div class="card-body">';
                                    
                                    // Field mappings in this child table
                                    html += '<table class="table table-sm" style="color: var(--text-color);">';
                                    html += '<thead><tr>';
                                    html += '<th>' + __('Source Field') + '</th>';
                                    html += '<th>' + __('Target Field') + '</th>';
                                    html += '</tr></thead>';
                                    html += '<tbody>';
                                    
                                    Object.entries(mapping.fields).forEach(function([src, tgt]) {
                                        html += '<tr>';
                                        html += '<td>' + src + '</td>';
                                        html += '<td>' + tgt + '</td>';
                                        html += '</tr>';
                                    });
                                    
                                    html += '</tbody></table>';
                                    
                                    // Sample data if available
                                    if (Object.keys(mapping.sample_data).length > 0) {
                                        html += '<div class="mt-2">';
                                        html += '<p><strong>' + __('Sample data from first row') + ':</strong></p>';
                                        html += '<pre class="small p-2" style="background: var(--control-bg); color: var(--text-color);">' + JSON.stringify(mapping.sample_data, null, 2) + '</pre>';
                                        html += '</div>';
                                    }
                                    
                                    html += '</div>'; // card-body
                                    html += '</div>'; // card
                                });
                            }
                            
                            // Hooks information
                            if (r.message.hooks && Object.keys(r.message.hooks).length > 0) {
                                html += '<h5>' + __('Custom Hooks') + '</h5>';
                                html += '<table class="table table-bordered" style="color: var(--text-color); background: var(--card-bg);">';
                                html += '<thead style="background: var(--control-bg);"><tr>';
                                html += '<th>' + __('Hook Type') + '</th>';
                                html += '<th>' + __('Function') + '</th>';
                                html += '</tr></thead>';
                                html += '<tbody>';
                                
                                if (r.message.hooks.before_sync) {
                                    html += '<tr>';
                                    html += '<td>' + __('Before Sync') + '</td>';
                                    html += '<td>' + r.message.hooks.before_sync + '</td>';
                                    html += '</tr>';
                                }
                                
                                if (r.message.hooks.after_sync) {
                                    html += '<tr>';
                                    html += '<td>' + __('After Sync') + '</td>';
                                    html += '<td>' + r.message.hooks.after_sync + '</td>';
                                    html += '</tr>';
                                }
                                
                                html += '</tbody></table>';
                            }
                            
                            html += '</div>'; // main div
                            
                            var d = new frappe.ui.Dialog({
                                title: __('Test Sync Results'),
                                size: 'large',
                                fields: [{
                                    fieldtype: 'HTML',
                                    fieldname: 'results',
                                    options: html
                                }],
                                primary_action_label: __('Close'),
                                primary_action: function() {
                                    d.hide();
                                }
                            });
                            
                            d.show();
                            
                            // Make sure actions are styled as filled buttons
                            setTimeout(function() {
                                d.$wrapper.find('.btn-primary').addClass('btn-fill');
                            }, 100);
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message ? r.message.message : __('An error occurred during test')
                            });
                        }
                    }
                });
            }, __('Test Sync'), __('Test'));
        }, __('Actions')).addClass('btn-fill');
        
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
        }, __('Actions')).addClass('btn-fill');
        
        // Add simple bulk sync button
        frm.add_custom_button(__('Bulk Sync'), function() {
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
                    fieldname: 'field_name',
                    label: __('Filter Field Name'),
                    fieldtype: 'Data',
                    description: __('Field name to filter by (e.g., status)')
                },
                {
                    fieldname: 'field_value',
                    label: __('Filter Value'),
                    fieldtype: 'Data',
                    description: __('Value to filter by (e.g., Active)')
                },
                {
                    fieldname: 'limit',
                    label: __('Maximum Documents'),
                    fieldtype: 'Int',
                    default: 100
                }
            ], function(values) {
                // Build filters
                let filters = {};
                if (values.field_name && values.field_value) {
                    filters[values.field_name] = values.field_value;
                }
                
                // Call method
                frm.call({
                    method: 'trigger_bulk_sync',
                    doc: frm.doc,
                    args: {
                        source_doctype: values.doctype,
                        filters: filters,
                        limit: values.limit
                    },
                    freeze: true,
                    freeze_message: __('Starting bulk sync...'),
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: r.message.message
                            });
                            
                            // If we have detailed results, show them
                            if (r.message.results) {
                                show_bulk_sync_results(r.message.results);
                            }
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: r.message ? r.message.message : __('An error occurred')
                            });
                        }
                    }
                });
            }, __('Start Bulk Sync'));
        }, __('Actions')).addClass('btn-fill');
        
        // Add view logs button
        frm.add_custom_button(__('View Logs'), function() {
            frappe.set_route('List', 'Sync Log', {sync_configuration: frm.doc.name});
        }, __('Actions')).addClass('btn-fill');
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

// Function to show bulk sync results
function show_bulk_sync_results(results) {
    let html = '<div style="color: var(--text-color);">';
    
    html += '<div class="row">';
    html += '<div class="col-md-4">';
    html += '<div class="stat-box" style="padding: 15px; text-align: center; background-color: var(--control-bg); border-radius: 4px; margin-bottom: 10px;">';
    html += '<div class="stat-label" style="font-size: 14px; font-weight: bold;">' + __('Total') + '</div>';
    html += '<div class="stat-value" style="font-size: 24px; font-weight: bold;">' + results.total + '</div>';
    html += '</div>';
    html += '</div>';
    
    html += '<div class="col-md-4">';
    html += '<div class="stat-box" style="padding: 15px; text-align: center; background-color: var(--control-bg); border-radius: 4px; margin-bottom: 10px;">';
    html += '<div class="stat-label" style="font-size: 14px; font-weight: bold; color: var(--success-color);">' + __('Succeeded') + '</div>';
    html += '<div class="stat-value" style="font-size: 24px; font-weight: bold; color: var(--success-color);">' + results.succeeded + '</div>';
    html += '</div>';
    html += '</div>';
    
    html += '<div class="col-md-4">';
    html += '<div class="stat-box" style="padding: 15px; text-align: center; background-color: var(--control-bg); border-radius: 4px; margin-bottom: 10px;">';
    html += '<div class="stat-label" style="font-size: 14px; font-weight: bold; color: var(--error-color);">' + __('Failed') + '</div>';
    html += '<div class="stat-value" style="font-size: 24px; font-weight: bold; color: var(--error-color);">' + results.failed + '</div>';
    html += '</div>';
    html += '</div>';
    html += '</div>';
    
    if (results.details && results.details.length > 0) {
        html += '<h5 class="mt-4">' + __('Details') + '</h5>';
        html += '<div style="max-height: 300px; overflow-y: auto;">';
        html += '<table class="table table-condensed table-bordered" style="color: var(--text-color); background: var(--card-bg);">';
        html += '<thead style="background: var(--control-bg);"><tr>';
        html += '<th>' + __('Document') + '</th>';
        html += '<th>' + __('Status') + '</th>';
        html += '<th>' + __('Error') + '</th>';
        html += '</tr></thead>';
        html += '<tbody>';
        
        results.details.forEach(function(detail) {
            html += '<tr>';
            html += '<td>' + detail.name + '</td>';
            html += '<td>' + (detail.status === 'Success' ? 
                '<span style="color: var(--success-color);">' + __('Success') + '</span>' : 
                '<span style="color: var(--error-color);">' + __('Failed') + '</span>') + 
                '</td>';
            html += '<td>' + (detail.error || '') + '</td>';
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        html += '</div>';
    }
    
    html += '</div>';
    
    let d = new frappe.ui.Dialog({
        title: __('Bulk Sync Results'),
        size: 'large',
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'results',
            options: html
        }],
        primary_action_label: __('Close'),
        primary_action: function() {
            d.hide();
        }
    });
    
    d.show();
    
    // Make sure actions are styled as filled buttons
    setTimeout(function() {
        d.$wrapper.find('.btn-primary').addClass('btn-fill');
    }, 100);
}