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

        // Configure button (separate)
        if (!frm.custom_buttons['Configure Sync Config']) {
            frm.add_custom_button(__('Configure Sync Config'), function() {
                open_sync_config_dialog(frm);
            }).addClass('btn-fill');
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
                            show_test_results(r.message);
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
                },
                {
                    fieldname: 'fast_mode',
                    label: __('Fast Mode'),
                    fieldtype: 'Check',
                    default: 0,
                    description: __('Bypass validations and hooks for better performance (use with caution)')
                }
            ], function(values) {
                frm.call({
                    method: 'trigger_sync_for_document',
                    doc: frm.doc,
                    args: {
                        doctype: values.doctype,
                        docname: values.docname,
                        fast_mode: values.fast_mode
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
        
        // Add bulk sync button
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
                },
                {
                    fieldname: 'fast_mode',
                    label: __('Fast Mode'),
                    fieldtype: 'Check',
                    default: 0,
                    description: __('Bypass validations and hooks for better performance (use with caution)')
                }
            ], function(values) {
                // Build filters
                var filters = {};
                if (values.field_name && values.field_value) {
                    filters[values.field_name] = values.field_value;
                }
                
                // Create progress dialog
                var progress_dialog = create_progress_dialog();
                
                // Call method
                frm.call({
                    method: 'trigger_bulk_sync',
                    doc: frm.doc,
                    args: {
                        source_doctype: values.doctype,
                        filters: filters,
                        limit: values.limit,
                        fast_mode: values.fast_mode
                    },
                    callback: function(r) {
                        handle_bulk_sync_response(r, progress_dialog);
                    }
                });
            }, __('Start Bulk Sync'));
        }, __('Actions')).addClass('btn-fill');

        // Add view running jobs button
        frm.add_custom_button(__('View Running Jobs'), function() {
            view_running_jobs(frm);
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

// Create progress dialog
function create_progress_dialog() {
    var progress_dialog = new frappe.ui.Dialog({
        title: __('Sync Progress'),
        fields: [
            {
                fieldname: 'progress_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            frappe.realtime.off('bulk_sync_progress');
            frappe.realtime.off('bulk_sync_completed');
            frappe.realtime.off('bulk_sync_error');
            progress_dialog.hide();
        }
    });

    // Render initial progress UI
    var $progress_wrapper = progress_dialog.fields_dict.progress_html.$wrapper;
    $progress_wrapper.html(
        '<div class="sync-progress">' +
        '    <div class="progress">' +
        '        <div class="progress-bar" style="width: 0%"></div>' +
        '    </div>' +
        '    <div class="progress-stats mt-3">' +
        '        <div class="row">' +
        '            <div class="col-md-6">' +
        '                <span class="processed font-weight-bold">Initializing...</span>' +
        '            </div>' +
        '            <div class="col-md-6 text-right">' +
        '                <span class="status font-weight-bold">Status: Starting...</span>' +
        '            </div>' +
        '        </div>' +
        '        <div class="row mt-2">' +
        '            <div class="col-md-6">' +
        '                <span class="created text-success">Created/Updated: -</span>' +
        '            </div>' +
        '            <div class="col-md-6 text-right">' +
        '                <span class="failed text-danger">Failed: -</span>' +
        '            </div>' +
        '        </div>' +
        '    </div>' +
        '</div>'
    );
    
    progress_dialog.show();
    
    // Set up listeners for real-time updates
    frappe.realtime.on('bulk_sync_progress', function(data) {
        updateProgressUI(data);
    });
    
    frappe.realtime.on('bulk_sync_completed', function(data) {
        $progress_wrapper.find('.status').text('Status: Completed');
        $progress_wrapper.find('.progress-bar').css('width', '100%');
        $progress_wrapper.find('.processed').text('Processed: ' + data.processed + '/' + data.processed);
        $progress_wrapper.find('.created').text('Created/Updated: ' + data.succeeded);
        $progress_wrapper.find('.failed').text('Failed: ' + data.failed);
        
        frappe.show_alert({
            message: __('Sync completed. ' + data.succeeded + ' created/updated, ' + data.failed + ' failed out of ' + data.processed + ' documents.'),
            indicator: 'green'
        }, 8);
        
        show_bulk_sync_results(data);
    });
    
    frappe.realtime.on('bulk_sync_error', function(data) {
        $progress_wrapper.find('.status').html('Status: <span class="text-danger">Error: ' + data.error + '</span>');
        
        frappe.show_alert({
            message: __('Sync failed: ' + data.error),
            indicator: 'red'
        }, 5);
    });
    
    return progress_dialog;
}

// Handle bulk sync response
function handle_bulk_sync_response(r, progress_dialog) {
    if (!r.message || !r.message.success) {
        // Show error in progress dialog
        progress_dialog.fields_dict.progress_html.$wrapper.find('.status').html('Status: <span class="text-danger">Error</span>');
        progress_dialog.fields_dict.progress_html.$wrapper.append('<div class="mt-3 text-danger">' + (r.message && r.message.message || "Unknown error") + '</div>');
        
        // Show error message
        frappe.msgprint({
            title: __('Error'),
            indicator: 'red',
            message: r.message ? r.message.message : __('An error occurred')
        });
        return;
    }
    
    var $progress_wrapper = progress_dialog.fields_dict.progress_html.$wrapper;
    
    if (r.message.job_id) {
        // Background job started
        $progress_wrapper.find('.status').text('Status: Processing in background...');
        $progress_wrapper.find('.processed').text('Processed: 0/' + r.message.total_docs);
        
        frappe.show_alert({
            message: __('Bulk sync started in background for ' + r.message.total_docs + ' documents.'),
            indicator: 'blue'
        }, 8);
    } else if (r.message.results) {
        // Direct processing completed
        var results = r.message.results;
        
        $progress_wrapper.find('.progress-bar').css('width', '100%');
        $progress_wrapper.find('.processed').text('Processed: ' + results.processed + '/' + results.total);
        $progress_wrapper.find('.created').text('Created/Updated: ' + results.succeeded);
        $progress_wrapper.find('.failed').text('Failed: ' + results.failed);
        $progress_wrapper.find('.status').text('Status: Completed');
        
        frappe.msgprint({
            title: __('Success'),
            indicator: 'green',
            message: r.message.message
        });
        
        show_bulk_sync_results(results);
    }
}

// Helper function to update progress UI
function updateProgressUI(data) {
    var percent = data.percent || 0;
    var $progress_dialogs = $(".modal-dialog:visible").find(".sync-progress");
    
    if ($progress_dialogs.length) {
        $progress_dialogs.each(function() {
            var $progress = $(this);
            $progress.find('.progress-bar').css('width', percent + '%');
            $progress.find('.processed').text('Processed: ' + data.processed + '/' + data.total);
            $progress.find('.created').text('Created/Updated: ' + data.succeeded);
            $progress.find('.failed').text('Failed: ' + data.failed);
        });
    }
}

// View running jobs
function view_running_jobs(frm) {
    frappe.call({
        method: 'core.sync_handler.get_bulk_sync_jobs',
        args: {
            sync_config: frm.doc.name
        },
        callback: function(r) {
            if (!r.message || !r.message.success) {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message ? r.message.message : __('Error retrieving jobs list'),
                    indicator: 'red'
                });
                return;
            }
            
            var jobs = r.message.jobs || [];
            
            if (jobs.length === 0) {
                frappe.msgprint({
                    title: __('No Running Jobs'),
                    message: __('There are no running or recent sync jobs for this configuration.'),
                    indicator: 'blue'
                });
                return;
            }
            
            show_jobs_dialog(jobs, frm);
        }
    });
}

// Show jobs dialog
function show_jobs_dialog(jobs, frm) {
    var d = new frappe.ui.Dialog({
        title: __('Sync Jobs Status'),
        fields: [
            {
                fieldname: 'jobs_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('Refresh'),
        primary_action: function() {
            view_running_jobs(frm);
            d.hide();
        },
        secondary_action_label: __('Close'),
        secondary_action: function() {
            d.hide();
        }
    });
    
    // Create HTML for the jobs list
    var $jobs_wrapper = d.fields_dict.jobs_html.$wrapper;
    var html = create_jobs_list_html(jobs);
    
    // Set the HTML and show the dialog
    $jobs_wrapper.html(html);
    d.show();
    
    // Add click handler for the view details button
    $jobs_wrapper.find('.view-job-details').on('click', function() {
        var jobId = $(this).data('job-id');
        get_job_details(jobId);
    });
    
    // Style buttons
    d.$wrapper.find('.btn-primary, .btn-secondary').addClass('btn-fill');
}

// Create jobs list HTML
function create_jobs_list_html(jobs) {
    var html = '<div class="jobs-list" style="color: var(--text-color);">';
    
    // Create a table for the jobs
    html += '<table class="table table-bordered" style="color: var(--text-color); background: var(--card-bg);">';
    html += '<thead style="background: var(--control-bg);"><tr>';
    html += '<th>' + __('Started At') + '</th>';
    html += '<th>' + __('Status') + '</th>';
    html += '<th>' + __('Progress') + '</th>';
    html += '<th>' + __('Actions') + '</th>';
    html += '</tr></thead>';
    html += '<tbody>';
    
    // Add each job to the table
    for (var i = 0; i < jobs.length; i++) {
        var job = jobs[i];
        var start_time = job.start_time ? frappe.datetime.str_to_user(job.start_time) : '';
        var status_class = job.status === 'Completed' ? 'text-success' : 
                          (job.status === 'Error' ? 'text-danger' : 'text-primary');
        
        html += '<tr>';
        html += '<td>' + start_time + '</td>';
        html += '<td class="' + status_class + '">' + job.status + '</td>';
        html += '<td>';
        
        // Add progress bar
        var percent = job.percent || 0;
        html += '<div class="progress" style="height: 10px;">';
        html += '<div class="progress-bar" role="progressbar" style="width: ' + percent + '%" ';
        html += 'aria-valuenow="' + percent + '" aria-valuemin="0" aria-valuemax="100"></div>';
        html += '</div>';
        html += '<div class="small text-center mt-1">' + percent + '% (' + job.processed + '/' + job.total + ')</div>';
        html += '</td>';
        
        // Add actions
        html += '<td>';
        html += '<button class="btn btn-xs btn-default view-job-details" data-job-id="' + job.job_id + '">';
        html += '<i class="fa fa-eye"></i> ' + __('View Details') + '</button>';
        html += '</td>';
        
        html += '</tr>';
    }
    
    html += '</tbody></table>';
    html += '</div>';
    
    return html;
}

// Get job details
function get_job_details(jobId) {
    frappe.call({
        method: 'core.sync_handler.get_bulk_sync_job_status',
        args: {
            job_id: jobId
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                show_bulk_sync_results(r.message.data);
            } else {
                frappe.msgprint({
                    title: __('Job Status Error'),
                    message: r.message && r.message.message || __('Error retrieving job status'),
                    indicator: 'red'
                });
            }
        }
    });
}

// Show test results
function show_test_results(data) {
    // Build a comprehensive HTML report
    var html = '<div class="sync-preview" style="color: var(--text-color);">';
    
    // Basic info
    html += '<div class="row">';
    html += '<div class="col-md-6">';
    html += '<p><strong>' + __('Source') + ':</strong> ' + data.source_doctype + ' - ' + data.source_doc + '</p>';
    html += '</div>';
    html += '<div class="col-md-6">';
    if (data.target_exists) {
        html += '<p><strong>' + __('Target') + ':</strong> ' + data.target_doctype + ' - ' + data.target_doc + '</p>';
        html += '<p style="color: var(--success-color);"><i class="fa fa-check"></i> ' + __('Target document exists, it would be updated') + '</p>';
    } else {
        html += '<p><strong>' + __('Target') + ':</strong> ' + data.target_doctype + ' - ' + __('New document would be created') + '</p>';
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
    
    for (var i = 0; i < data.field_mappings.length; i++) {
        var mapping = data.field_mappings[i];
        html += '<tr>';
        html += '<td>' + mapping.source_field + '</td>';
        html += '<td>' + mapping.target_field + '</td>';
        html += '<td>' + (mapping.value !== null && mapping.value !== undefined ? mapping.value : '') + '</td>';
        html += '<td>' + (mapping.transform || '') + '</td>';
        html += '</tr>';
    }
    
    html += '</tbody></table>';
    
    // Child table mappings
    if (data.child_mappings && data.child_mappings.length > 0) {
        html += '<h5>' + __('Child Table Mappings') + '</h5>';
        
        for (var i = 0; i < data.child_mappings.length; i++) {
            var mapping = data.child_mappings[i];
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
            
            for (var key in mapping.fields) {
                if (mapping.fields.hasOwnProperty(key)) {
                    var value = mapping.fields[key];
                    html += '<tr>';
                    html += '<td>' + key + '</td>';
                    html += '<td>' + value + '</td>';
                    html += '</tr>';
                }
            }
            
            html += '</tbody></table>';
            
            // Sample data if available
            if (mapping.sample_data && Object.keys(mapping.sample_data).length > 0) {
                html += '<div class="mt-2">';
                html += '<p><strong>' + __('Sample data from first row') + ':</strong></p>';
                html += '<pre class="small p-2" style="background: var(--control-bg); color: var(--text-color);">' + JSON.stringify(mapping.sample_data, null, 2) + '</pre>';
                html += '</div>';
            }
            
            html += '</div>'; // card-body
            html += '</div>'; // card
        }
    }
    
    // Hooks information
    if (data.hooks && Object.keys(data.hooks).length > 0) {
        html += '<h5>' + __('Custom Hooks') + '</h5>';
        html += '<table class="table table-bordered" style="color: var(--text-color); background: var(--card-bg);">';
        html += '<thead style="background: var(--control-bg);"><tr>';
        html += '<th>' + __('Hook Type') + '</th>';
        html += '<th>' + __('Function') + '</th>';
        html += '</tr></thead>';
        html += '<tbody>';
        
        if (data.hooks.before_sync) {
            html += '<tr>';
            html += '<td>' + __('Before Sync') + '</td>';
            html += '<td>' + data.hooks.before_sync + '</td>';
            html += '</tr>';
        }
        
        if (data.hooks.after_sync) {
            html += '<tr>';
            html += '<td>' + __('After Sync') + '</td>';
            html += '<td>' + data.hooks.after_sync + '</td>';
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
}

// Function to show bulk sync results
function show_bulk_sync_results(results) {
    var html = '<div style="color: var(--text-color);">';
    
    // Summary statistics section
    html += '<div class="row">';
    html += '<div class="col-md-4">';
    html += '<div class="stat-box" style="padding: 15px; text-align: center; background-color: var(--control-bg); border-radius: 4px; margin-bottom: 10px;">';
    html += '<div class="stat-label" style="font-size: 14px; font-weight: bold;">' + __('Total') + '</div>';
    html += '<div class="stat-value" style="font-size: 24px; font-weight: bold;">' + (results.total || results.processed || 0) + '</div>';
    html += '</div>';
    html += '</div>';
    
    html += '<div class="col-md-4">';
    html += '<div class="stat-box" style="padding: 15px; text-align: center; background-color: var(--control-bg); border-radius: 4px; margin-bottom: 10px;">';
    html += '<div class="stat-label" style="font-size: 14px; font-weight: bold; color: var(--success-color);">' + __('Succeeded') + '</div>';
    html += '<div class="stat-value" style="font-size: 24px; font-weight: bold; color: var(--success-color);">' + (results.succeeded || 0) + '</div>';
    html += '</div>';
    html += '</div>';
    
    html += '<div class="col-md-4">';
    html += '<div class="stat-box" style="padding: 15px; text-align: center; background-color: var(--control-bg); border-radius: 4px; margin-bottom: 10px;">';
    html += '<div class="stat-label" style="font-size: 14px; font-weight: bold; color: var(--error-color);">' + __('Failed') + '</div>';
    html += '<div class="stat-value" style="font-size: 24px; font-weight: bold; color: var(--error-color);">' + (results.failed || 0) + '</div>';
    html += '</div>';
    html += '</div>';
    html += '</div>';
    
    // Add job details if available
    if (results.job_id) {
        var start_time = results.start_time ? frappe.datetime.str_to_user(results.start_time) : '';
        var end_time = results.end_time ? frappe.datetime.str_to_user(results.end_time) : '';
        
        // Calculate duration if possible
        var duration = '';
        if (results.start_time && results.end_time) {
            var start = moment(results.start_time);
            var end = moment(results.end_time);
            var diff = moment.duration(end.diff(start));
            duration = Math.floor(diff.asMinutes()) + 'm ' + diff.seconds() + 's';
        }
        
        html += '<div class="job-details mb-4" style="background-color: var(--control-bg); padding: 15px; border-radius: 4px; margin-top: 15px;">';
        html += '<div class="row">';
        html += '<div class="col-md-6">';
        html += '<p><strong>' + __('Job ID') + ':</strong> ' + results.job_id + '</p>';
        html += '<p><strong>' + __('Start Time') + ':</strong> ' + (start_time || 'N/A') + '</p>';
        html += '</div>';
        html += '<div class="col-md-6">';
        html += '<p><strong>' + __('Status') + ':</strong> ' + (results.status || 'Completed') + '</p>';
        html += '<p><strong>' + __('End Time') + ':</strong> ' + (end_time || 'N/A') + '</p>';
        html += '</div>';
        html += '</div>';
        if (duration) {
            html += '<p><strong>' + __('Duration') + ':</strong> ' + duration + '</p>';
        }
        html += '</div>';
    }
    
    // Show detailed results if available
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
        
        for (var i = 0; i < results.details.length; i++) {
            var detail = results.details[i];
            html += '<tr>';
            html += '<td>' + detail.name + '</td>';
            html += '<td>' + (detail.status === 'Success' ? 
                '<span style="color: var(--success-color);">' + __('Success') + '</span>' : 
                '<span style="color: var(--error-color);">' + __('Failed') + '</span>') + 
                '</td>';
            html += '<td>' + (detail.error || '') + '</td>';
            html += '</tr>';
        }
        
        html += '</tbody></table>';
        html += '</div>';
    }
    
    // Add error message if present
    if (results.error) {
        html += '<div class="error-section mt-3">';
        html += '<div class="alert alert-danger">';
        html += '<strong>' + __('Error') + ':</strong> ' + results.error;
        html += '</div>';
        html += '</div>';
    }
    
    html += '</div>'; // Close main container
    
    var d = new frappe.ui.Dialog({
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

// Open sync configuration dialog

function open_sync_config_dialog(frm) {
    var src = frm.doc.source_doctype;
    var tgt = frm.doc.target_doctype;
    if (!src || !tgt) {
        frappe.msgprint(__('Please set both Source and Target DocTypes first.'));
        return;
    }
    
    frappe.model.with_doctype(src, function() {
        frappe.model.with_doctype(tgt, function() {
            var src_meta = frappe.get_meta(src);
            var tgt_meta = frappe.get_meta(tgt);

            // Create field lists with better display
            function create_field_options(meta) {
                var fields = [];
                meta.fields.forEach(function(f) {
                    // Skip common system fields
                    if (['owner', 'creation', 'modified', 'modified_by', 'docstatus', 'idx'].includes(f.fieldname)) {
                        return;
                    }
                    
                    fields.push({
                        value: f.fieldname,
                        label: f.label + ' (' + f.fieldname + ') [' + f.fieldtype + ']'
                    });
                });
                
                // Sort alphabetically by label
                fields.sort(function(a, b) {
                    return a.label.localeCompare(b.label);
                });
                
                // Add 'name' field
                fields.unshift({
                    value: 'name',
                    label: 'Name (name) [Data]'
                });
                
                return fields;
            }
            
            // Get field metadata maps for reference
            function create_field_metadata_map(meta) {
                var map = {
                    'name': { fieldtype: 'Data', label: 'Name' }
                };
                
                meta.fields.forEach(function(f) {
                    map[f.fieldname] = {
                        fieldtype: f.fieldtype,
                        label: f.label || f.fieldname
                    };
                });
                
                return map;
            }
            
            var source_fields = create_field_options(src_meta);
            var target_fields = create_field_options(tgt_meta);
            var src_field_meta = create_field_metadata_map(src_meta);
            var tgt_field_meta = create_field_metadata_map(tgt_meta);
            
            // Get child tables
            function get_child_tables(meta) {
                var tables = [];
                meta.fields.forEach(function(f) {
                    if (f.fieldtype === 'Table') {
                        tables.push({
                            value: f.fieldname,
                            label: (f.label || f.fieldname) + ' (' + f.fieldname + ')'
                        });
                    }
                });
                return tables;
            }
            
            var source_tables = get_child_tables(src_meta);
            var target_tables = get_child_tables(tgt_meta);

            var d = new frappe.ui.Dialog({
                title: __('Configure Sync Configuration'),
                size: 'large',
                fields: [
                    { fieldtype: 'HTML', fieldname: 'beta_info', options: '<p><em>Use this form to manage all sync settings.</em></p>' },
                    
                    // IDENTIFIER MAPPING SECTION
                    { fieldtype: 'Section Break', label: __('Identifier Mapping') },
                    { fieldtype: 'HTML', fieldname: 'identifier_help', options: '<p><small>Identifier fields are used to find matching documents between systems. These fields should contain unique values (e.g., email, ID number).</small></p>' },
                    { fieldtype: 'Table', fieldname: 'identifier_mapping', label: __('Identifier Field Mappings'), in_place: true,
                      cannot_add_rows: false, data: [{'source_field':'', 'source_fieldtype':'', 'target_field':'', 'target_fieldtype':''}],
                      fields: [
                          { fieldtype: 'Select', fieldname: 'source_field', label: __('Source Field'), options: source_fields, reqd:1, "in_list_view": 1, 
                            change: function(e) {
                                var grid_row = cur_frm.get_field("identifier_mapping").grid.get_row(this.doc.idx - 1);
                                var field = this.doc.source_field;
                                if (field && src_field_meta[field]) {
                                    grid_row.doc.source_fieldtype = src_field_meta[field].fieldtype;
                                    grid_row.refresh();
                                }
                            }
                          },
                          { fieldtype: 'Data', fieldname: 'source_fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 },
                          { fieldtype: 'Select', fieldname: 'target_field', label: __('Target Field'), options: target_fields, reqd:1, "in_list_view": 1,
                            change: function(e) {
                                var grid_row = cur_frm.get_field("identifier_mapping").grid.get_row(this.doc.idx - 1);
                                var field = this.doc.target_field;
                                if (field && tgt_field_meta[field]) {
                                    grid_row.doc.target_fieldtype = tgt_field_meta[field].fieldtype;
                                    grid_row.refresh();
                                }
                            }
                          },
                          { fieldtype: 'Data', fieldname: 'target_fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 }
                      ]
                    },
                    
                    // DIRECT FIELD MAPPINGS SECTION
                    { fieldtype: 'Section Break', label: __('Direct Field Mappings') },
                    { fieldtype: 'Table', fieldname: 'direct_fields', label: __('Direct Field Mappings'), in_place: true,
                      cannot_add_rows: false, data: [{'source_field':'', 'source_fieldtype':'', 'target_field':'', 'target_fieldtype':''}],
                      fields: [
                          { fieldtype: 'Select', fieldname: 'source_field', label: __('Source Field'), options: source_fields, reqd:1, "in_list_view": 1,
                            change: function(e) {
                                var grid_row = cur_frm.get_field("direct_fields").grid.get_row(this.doc.idx - 1);
                                var field = this.doc.source_field;
                                if (field && src_field_meta[field]) {
                                    grid_row.doc.source_fieldtype = src_field_meta[field].fieldtype;
                                    grid_row.refresh();
                                }
                            }
                          },
                          { fieldtype: 'Data', fieldname: 'source_fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 },
                          { fieldtype: 'Select', fieldname: 'target_field', label: __('Target Field'), options: target_fields, reqd:1, "in_list_view": 1,
                            change: function(e) {
                                var grid_row = cur_frm.get_field("direct_fields").grid.get_row(this.doc.idx - 1);
                                var field = this.doc.target_field;
                                if (field && tgt_field_meta[field]) {
                                    grid_row.doc.target_fieldtype = tgt_field_meta[field].fieldtype;
                                    grid_row.refresh();
                                }
                            }
                          },
                          { fieldtype: 'Data', fieldname: 'target_fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 }
                      ]
                    },
                    
                    // CHILD MAPPINGS SECTION
                    { fieldtype: 'Section Break', label: __('Child Table Mappings') },
                    { fieldtype: 'Table', fieldname: 'child_mappings', label: __('Child Table Mappings'), in_place: true,
                      cannot_add_rows: false, data: [{'source_table':'', 'target_table':'', 'fields_map':''}],
                      fields: [
                          { fieldtype: 'Select', fieldname: 'source_table', label: __('Source Table'), options: source_tables, reqd:1, "in_list_view": 1 },
                          { fieldtype: 'Select', fieldname: 'target_table', label: __('Target Table'), options: target_tables, reqd:1, "in_list_view": 1 },
                          { fieldtype: 'Small Text', fieldname:'fields_map', label: __('Field Map (JSON)'), reqd:1, "in_list_view": 1 },
                          { fieldtype: 'Button', fieldname: 'config_child_mapping', label: __('Configure Fields'),
                            click: function() {
                                var grid_row = cur_frm.get_field("child_mappings").grid.get_row(this.doc.idx - 1);
                                var source_table = grid_row.doc.source_table;
                                var target_table = grid_row.doc.target_table;
                                
                                if (!source_table || !target_table) {
                                    frappe.msgprint(__("Please select both source and target tables first"));
                                    return;
                                }
                                
                                // Get the child doctypes
                                var source_child_doctype = "";
                                var target_child_doctype = "";
                                
                                src_meta.fields.forEach(function(f) {
                                    if (f.fieldname === source_table && f.fieldtype === 'Table') {
                                        source_child_doctype = f.options;
                                    }
                                });
                                
                                tgt_meta.fields.forEach(function(f) {
                                    if (f.fieldname === target_table && f.fieldtype === 'Table') {
                                        target_child_doctype = f.options;
                                    }
                                });
                                
                                if (!source_child_doctype || !target_child_doctype) {
                                    frappe.msgprint(__("Could not determine child doctypes"));
                                    return;
                                }
                                
                                // Load the child doctypes and open a config dialog
                                frappe.model.with_doctype(source_child_doctype, function() {
                                    frappe.model.with_doctype(target_child_doctype, function() {
                                        open_child_mapping_dialog(
                                            source_child_doctype, 
                                            target_child_doctype,
                                            grid_row.doc
                                        );
                                    });
                                });
                            }
                          }
                      ]
                    },
                    
                    // DEFAULT VALUES SECTION
                    { fieldtype: 'Section Break', label: __('Default Values') },
                    { fieldtype: 'HTML', fieldname: 'default_help', options: '<p><small>Default values are applied to target fields when creating new documents.</small></p>' },
                    { fieldtype: 'Table', fieldname: 'default_values', label: __('Default Values'), in_place: true,
                      cannot_add_rows: false, data: [{'fieldname':'', 'fieldtype':'', 'default_value':''}],
                      fields: [
                          { fieldtype: 'Select', fieldname: 'fieldname', label: __('Field'), options: target_fields, reqd:1, "in_list_view": 1,
                            change: function(e) {
                                var grid_row = cur_frm.get_field("default_values").grid.get_row(this.doc.idx - 1);
                                var field = this.doc.fieldname;
                                if (field && tgt_field_meta[field]) {
                                    grid_row.doc.fieldtype = tgt_field_meta[field].fieldtype;
                                    grid_row.refresh();
                                }
                            }
                          },
                          { fieldtype: 'Data', fieldname: 'fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 },
                          { fieldtype: 'Data', fieldname: 'default_value', label: __('Default Value'), reqd:1, "in_list_view": 1 }
                      ]
                    },
                    
                    // TRANSFORMS SECTION
                    { fieldtype: 'Section Break', label: __('Transforms') },
                    { fieldtype: 'HTML', fieldname: 'transform_help', options: '<p><small>Transforms allow you to modify field values during sync using custom Python functions.</small></p>' },
                    { fieldtype: 'Table', fieldname: 'transforms', label: __('Transforms'), in_place: true,
                      cannot_add_rows: false, data: [{'fieldname':'', 'fieldtype':'', 'function_path':''}],
                      fields: [
                          { fieldtype: 'Select', fieldname: 'fieldname', label: __('Source Field'), options: source_fields, reqd:1, "in_list_view": 1,
                            change: function(e) {
                                var grid_row = cur_frm.get_field("transforms").grid.get_row(this.doc.idx - 1);
                                var field = this.doc.fieldname;
                                if (field && src_field_meta[field]) {
                                    grid_row.doc.fieldtype = src_field_meta[field].fieldtype;
                                    grid_row.refresh();
                                }
                            }
                          },
                          { fieldtype: 'Data', fieldname: 'fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 },
                          { fieldtype: 'Data', fieldname: 'function_path', label: __('Transform Function Path'), reqd:1, "in_list_view": 1,
                            description: __('Python function path (e.g., module.submodule.transform_function)')
                          }
                      ]
                    },
                    
                    // HOOKS SECTION
                    { fieldtype: 'Section Break', label: __('Hooks') },
                    { fieldtype: 'HTML', fieldname: 'hooks_help', options: '<p><small>Hooks allow for custom logic during the sync process. These should be paths to Python functions (e.g., module.submodule.function_name).</small></p>' },
                    { fieldtype: 'Data', fieldname: 'hooks_before', label: __('Before Sync Hook (Function Path)') },
                    { fieldtype: 'Data', fieldname: 'hooks_sync_name', label: __('Sync Name Hook (Function Path)'),
                      description: __('Optional. Controls document naming. Use "core.hook_helpers.set_name" to share names or "core.hook_helpers.sync_name" to create with same name.') },
                    { fieldtype: 'Data', fieldname: 'hooks_after',  label: __('After Sync Hook (Function Path)') },
                    
                    // OTHER OPTIONS
                    { fieldtype: 'Section Break', label: __('Other Options') },
                    { fieldtype: 'Check', fieldname: 'allow_recreate', label: __('Allow Recreate Deleted Targets') }
                ],
                // Add primary action instead of a save button field
                primary_action_label: __('Save Configuration'),
                primary_action: function() {
                    var vals = d.get_values();
                    
                    var newcfg = { 
                        direct_fields: {}, 
                        child_mappings: [], 
                        default_values: {}, 
                        transform: {}, 
                        hooks: {}, 
                        identifier_mapping: {},
                        allow_recreate: true 
                    };
                    
                    // Process direct fields
                    if (vals.direct_fields) {
                        for (var i = 0; i < vals.direct_fields.length; i++) {
                            var row = vals.direct_fields[i];
                            if (row.source_field && row.target_field) {
                                newcfg.direct_fields[row.source_field] = row.target_field;
                            }
                        }
                    }
                    
                    // Process child mappings
                    if (vals.child_mappings) {
                        for (var i = 0; i < vals.child_mappings.length; i++) {
                            var row = vals.child_mappings[i];
                            if (row.source_table && row.target_table && row.fields_map) {
                                try {
                                    var fields = JSON.parse(row.fields_map);
                                    newcfg.child_mappings.push({
                                        source_table: row.source_table,
                                        target_table: row.target_table,
                                        fields: fields.fields || fields, // handle both formats
                                        key_field: fields.key_field // include key_field if present
                                    });
                                } catch(e) {
                                    frappe.msgprint({
                                        message: __('Invalid JSON in child fields'),
                                        indicator: 'red'
                                    });
                                    return;
                                }
                            }
                        }
                    }
                    
                    // Process default values
                    if (vals.default_values) {
                        for (var i = 0; i < vals.default_values.length; i++) {
                            var row = vals.default_values[i];
                            if (row.fieldname && row.default_value) {
                                newcfg.default_values[row.fieldname] = row.default_value;
                            }
                        }
                    }
                    
                    // Process transforms
                    if (vals.transforms) {
                        for (var i = 0; i < vals.transforms.length; i++) {
                            var row = vals.transforms[i];
                            if (row.fieldname && row.function_path) {
                                newcfg.transform[row.fieldname] = row.function_path;
                            }
                        }
                    }
                    
                    // Process identifier mappings
                    if (vals.identifier_mapping) {
                        for (var i = 0; i < vals.identifier_mapping.length; i++) {
                            var row = vals.identifier_mapping[i];
                            if (row.source_field && row.target_field) {
                                newcfg.identifier_mapping[row.source_field] = row.target_field;
                            }
                        }
                    }
                    
                    // Set hooks
                    if (vals.hooks_before) newcfg.hooks.before_sync = vals.hooks_before;
                    if (vals.hooks_sync_name) newcfg.hooks.sync_name = vals.hooks_sync_name;
                    if (vals.hooks_after) newcfg.hooks.after_sync = vals.hooks_after;
                    
                    // Set allow_recreate
                    newcfg.allow_recreate = !!vals.allow_recreate;
                    
                    // Update form
                    frm.set_value('config', JSON.stringify(newcfg, null, 4));
                    d.hide();
                    
                    frappe.msgprint({
                        title: __('Configuration Updated'),
                        indicator: 'green',
                        message: __('Sync configuration has been updated.')
                    });
                }
            });

            // Function to open child mapping configuration dialog
            function open_child_mapping_dialog(source_child_doctype, target_child_doctype, row_doc) {
                var src_child_meta = frappe.get_meta(source_child_doctype);
                var tgt_child_meta = frappe.get_meta(target_child_doctype);
                
                // Create field options for source and target
                function create_child_field_options(meta) {
                    var fields = [];
                    meta.fields.forEach(function(f) {
                        if (!['owner', 'creation', 'modified', 'modified_by', 'docstatus', 'idx', 'parent', 'parenttype', 'parentfield'].includes(f.fieldname)) {
                            fields.push({
                                value: f.fieldname,
                                label: (f.label || f.fieldname) + ' (' + f.fieldname + ') [' + f.fieldtype + ']'
                            });
                        }
                    });
                    
                    // Sort alphabetically
                    fields.sort(function(a, b) {
                        return a.label.localeCompare(b.label);
                    });
                    
                    return fields;
                }
                
                var source_child_fields = create_child_field_options(src_child_meta);
                var target_child_fields = create_child_field_options(tgt_child_meta);
                
                // Create metadata maps
                function create_child_field_meta_map(meta) {
                    var map = {};
                    meta.fields.forEach(function(f) {
                        map[f.fieldname] = {
                            fieldtype: f.fieldtype,
                            label: f.label || f.fieldname
                        };
                    });
                    return map;
                }
                
                var src_child_field_meta = create_child_field_meta_map(src_child_meta);
                var tgt_child_field_meta = create_child_field_meta_map(tgt_child_meta);
                
                // Parse existing field mappings if any
                var existing_field_mappings = [];
                var key_field = '';
                
                if (row_doc.fields_map) {
                    try {
                        var mapping_obj = JSON.parse(row_doc.fields_map);
                        
                        // Handle both formats - old format is directly fields, new format has fields property
                        var fields_obj = mapping_obj.fields || mapping_obj;
                        
                        // Get key_field if present
                        key_field = mapping_obj.key_field || '';
                        
                        for (var src_field in fields_obj) {
                            if (fields_obj.hasOwnProperty(src_field)) {
                                var tgt_field = fields_obj[src_field];
                                existing_field_mappings.push({
                                    source_field: src_field,
                                    source_fieldtype: src_child_field_meta[src_field] ? src_child_field_meta[src_field].fieldtype : '',
                                    target_field: tgt_field,
                                    target_fieldtype: tgt_child_field_meta[tgt_field] ? tgt_child_field_meta[tgt_field].fieldtype : ''
                                });
                            }
                        }
                    } catch(e) {
                        // Invalid JSON, ignore
                        console.error("Error parsing fields_map: ", e);
                    }
                }
                
                // If no existing mappings, add an empty row
                if (existing_field_mappings.length === 0) {
                    existing_field_mappings.push({
                        source_field: '',
                        source_fieldtype: '',
                        target_field: '',
                        target_fieldtype: ''
                    });
                }
                
                // Create child mapping dialog
                var child_dialog = new frappe.ui.Dialog({
                    title: __('Configure Child Table Mapping'),
                    fields: [
                        { fieldtype: 'HTML', fieldname: 'info', options: `<p>
                            <strong>Source Table:</strong> ${row_doc.source_table} (${source_child_doctype})<br>
                            <strong>Target Table:</strong> ${row_doc.target_table} (${target_child_doctype})
                            </p>`
                        },
                        { fieldtype: 'Table', fieldname: 'field_mappings', label: __('Field Mappings'), in_place: true,
                          cannot_add_rows: false, data: existing_field_mappings,
                          fields: [
                              { fieldtype: 'Select', fieldname: 'source_field', label: __('Source Field'), options: source_child_fields, reqd:1, "in_list_view": 1,
                                change: function(e) {
                                    // Using child_dialog instead of cur_frm to avoid conflicts
                                    var grid_row = child_dialog.fields_dict.field_mappings.grid.get_row(this.doc.idx - 1);
                                    var field = this.doc.source_field;
                                    if (field && src_child_field_meta[field]) {
                                        grid_row.doc.source_fieldtype = src_child_field_meta[field].fieldtype;
                                        grid_row.refresh();
                                    }
                                }
                              },
                              { fieldtype: 'Data', fieldname: 'source_fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 },
                              { fieldtype: 'Select', fieldname: 'target_field', label: __('Target Field'), options: target_child_fields, reqd:1, "in_list_view": 1,
                                change: function(e) {
                                    // Using child_dialog instead of cur_frm
                                    var grid_row = child_dialog.fields_dict.field_mappings.grid.get_row(this.doc.idx - 1);
                                    var field = this.doc.target_field;
                                    if (field && tgt_child_field_meta[field]) {
                                        grid_row.doc.target_fieldtype = tgt_child_field_meta[field].fieldtype;
                                        grid_row.refresh();
                                    }
                                }
                              },
                              { fieldtype: 'Data', fieldname: 'target_fieldtype', label: __('Type'), read_only: 1, "in_list_view": 1 }
                          ]
                        },
                        { fieldtype: 'Section Break' },
                        { fieldtype: 'Select', fieldname: 'key_field', label: __('Key Field for Matching'),
                          options: source_child_fields.map(f => f.value),
                          description: __('Optional: Field used to match rows between source and target tables.'),
                          default: key_field
                        }
                    ],
                    primary_action_label: __('Update Mapping'),
                    primary_action: function() {
                        var values = child_dialog.get_values();
                        
                        // Build field mapping object
                        var field_map = {};
                        if (values.field_mappings) {
                            for (var i = 0; i < values.field_mappings.length; i++) {
                                var mapping = values.field_mappings[i];
                                if (mapping.source_field && mapping.target_field) {
                                    field_map[mapping.source_field] = mapping.target_field;
                                }
                            }
                        }
                        
                        // Create the final mapping object
                        var mapping_obj = {
                            fields: field_map
                        };
                        
                        if (values.key_field) {
                            mapping_obj.key_field = values.key_field;
                        }
                        
                        // Update the parent row
                        row_doc.fields_map = JSON.stringify(mapping_obj, null, 2);
                        
                        // Refresh the parent grid
                        d.fields_dict.child_mappings.grid.refresh();
                        
                        child_dialog.hide();
                    }
                });
                
                child_dialog.show();
            }

            // Parse existing config
            var cfg = {};
            try { 
                cfg = frm.doc.config ? JSON.parse(frm.doc.config) : {}; 
            } catch(e) {
                console.error("Error parsing config JSON:", e);
                cfg = {};
            }
            
            // Initialize config parts if they don't exist
            cfg.direct_fields = cfg.direct_fields || {};
            cfg.child_mappings = cfg.child_mappings || [];
            cfg.default_values = cfg.default_values || {};
            cfg.transform = cfg.transform || {};
            cfg.hooks = cfg.hooks || {};
            cfg.identifier_mapping = cfg.identifier_mapping || {};
            
            // ===== Build data arrays for each field type =====
            
            // 1. Direct field mappings
            var direct_fields_data = [];
            for (var src_field in cfg.direct_fields) {
                if (cfg.direct_fields.hasOwnProperty(src_field)) {
                    var tgt_field = cfg.direct_fields[src_field];
                    direct_fields_data.push({
                        source_field: src_field,
                        source_fieldtype: src_field_meta[src_field] ? src_field_meta[src_field].fieldtype : '',
                        target_field: tgt_field,
                        target_fieldtype: tgt_field_meta[tgt_field] ? tgt_field_meta[tgt_field].fieldtype : ''
                    });
                }
            }
            
            // 2. Child table mappings
            var child_mappings_data = [];
            for (var i = 0; i < cfg.child_mappings.length; i++) {
                var m = cfg.child_mappings[i];
                if (m && m.source_table && m.target_table) {
                    var fields_obj = m.fields || {};
                    
                    // Create a new mapping object that includes key_field if present
                    var mapping_obj = {
                        fields: fields_obj
                    };
                    
                    if (m.key_field) {
                        mapping_obj.key_field = m.key_field;
                    }
                    
                    child_mappings_data.push({
                        source_table: m.source_table,
                        target_table: m.target_table,
                        fields_map: JSON.stringify(mapping_obj, null, 2)
                    });
                }
            }
            
            // 3. Default values
            var default_values_data = [];
            for (var field in cfg.default_values) {
                if (cfg.default_values.hasOwnProperty(field)) {
                    default_values_data.push({
                        fieldname: field,
                        fieldtype: tgt_field_meta[field] ? tgt_field_meta[field].fieldtype : '',
                        default_value: cfg.default_values[field]
                    });
                }
            }
            
            // 4. Transforms
            var transforms_data = [];
            for (var field in cfg.transform) {
                if (cfg.transform.hasOwnProperty(field)) {
                    transforms_data.push({
                        fieldname: field,
                        fieldtype: src_field_meta[field] ? src_field_meta[field].fieldtype : '',
                        function_path: cfg.transform[field]
                    });
                }
            }
            
            // 5. Identifier mappings
            var identifier_mapping_data = [];
            for (var src_field in cfg.identifier_mapping) {
                if (cfg.identifier_mapping.hasOwnProperty(src_field)) {
                    var tgt_field = cfg.identifier_mapping[src_field];
                    identifier_mapping_data.push({
                        source_field: src_field,
                        source_fieldtype: src_field_meta[src_field] ? src_field_meta[src_field].fieldtype : '',
                        target_field: tgt_field,
                        target_fieldtype: tgt_field_meta[tgt_field] ? tgt_field_meta[tgt_field].fieldtype : ''
                    });
                }
            }
            
            // Set dialog values after a slight delay to ensure all fields are rendered
            setTimeout(function() {
                // Set direct fields
                if (direct_fields_data.length > 0) {
                    d.fields_dict.direct_fields.df.data = direct_fields_data;
                    d.fields_dict.direct_fields.grid.refresh();
                }
                
                // Set child mappings
                if (child_mappings_data.length > 0) {
                    d.fields_dict.child_mappings.df.data = child_mappings_data;
                    d.fields_dict.child_mappings.grid.refresh();
                }
                
                // Set default values
                if (default_values_data.length > 0) {
                    d.fields_dict.default_values.df.data = default_values_data;
                    d.fields_dict.default_values.grid.refresh();
                }
                
                // Set transforms
                if (transforms_data.length > 0) {
                    d.fields_dict.transforms.df.data = transforms_data;
                    d.fields_dict.transforms.grid.refresh();
                }
                
                // Set identifier mappings
                if (identifier_mapping_data.length > 0) {
                    d.fields_dict.identifier_mapping.df.data = identifier_mapping_data;
                    d.fields_dict.identifier_mapping.grid.refresh();
                }
                
                // Set hooks
                if (cfg.hooks) {
                    d.set_value('hooks_before', cfg.hooks.before_sync || '');
                    d.set_value('hooks_sync_name', cfg.hooks.sync_name || '');
                    d.set_value('hooks_after', cfg.hooks.after_sync || '');
                }
                
                // Set allow_recreate
                d.set_value('allow_recreate', cfg.allow_recreate === false ? 0 : 1);
                
                console.log("All values set!");
            }, 300);  // Small delay to ensure dialog is fully rendered

            d.show();
        });
    });
}