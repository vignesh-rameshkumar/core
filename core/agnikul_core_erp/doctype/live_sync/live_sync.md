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
                }
            ], function(values) {
                // Build filters
                let filters = {};
                if (values.field_name && values.field_value) {
                    filters[values.field_name] = values.field_value;
                }
                
                // Create progress dialog before making the call
                const progress_dialog = new frappe.ui.Dialog({
                    title: __('Sync Progress'),
                    fields: [
                        {
                            fieldname: 'progress_html',
                            fieldtype: 'HTML'
                        }
                    ],
                    primary_action_label: __('Close'),
                    primary_action: function() {
                        // Unsubscribe from socket events when dialog is closed
                        frappe.realtime.off('bulk_sync_progress');
                        frappe.realtime.off('bulk_sync_completed');
                        frappe.realtime.off('bulk_sync_error');
                        progress_dialog.hide();
                    }
                });
        
                // Render initial progress UI
                const $progress_wrapper = progress_dialog.fields_dict.progress_html.$wrapper;
                $progress_wrapper.html(`
                    <div class="sync-progress">
                        <div class="progress">
                            <div class="progress-bar" style="width: 0%"></div>
                        </div>
                        <div class="progress-stats mt-3">
                            <div class="row">
                                <div class="col-md-6">
                                    <span class="processed font-weight-bold">Initializing...</span>
                                </div>
                                <div class="col-md-6 text-right">
                                    <span class="status font-weight-bold">Status: Starting...</span>
                                </div>
                            </div>
                            <div class="row mt-2">
                                <div class="col-md-6">
                                    <span class="created text-success">Created/Updated: -</span>
                                </div>
                                <div class="col-md-6 text-right">
                                    <span class="failed text-danger">Failed: -</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `);
                
                progress_dialog.show();
                
                // DEBUG: Add event listeners before making the call
                // This will help us see if we're receiving events at all
                console.log("Setting up realtime listeners");
                
                // Set up listeners for real-time updates
                frappe.realtime.on('bulk_sync_progress', function(data) {
                    console.log("Received progress update:", data);
                    updateProgressUI(data);
                });
                
                frappe.realtime.on('bulk_sync_completed', function(data) {
                    console.log("Received completion notification:", data);
                    $progress_wrapper.find('.status').text('Status: Completed');
                    $progress_wrapper.find('.progress-bar').css('width', '100%');
                    $progress_wrapper.find('.processed').text(`Processed: ${data.processed}/${data.processed}`);
                    $progress_wrapper.find('.created').text(`Created/Updated: ${data.succeeded}`);
                    $progress_wrapper.find('.failed').text(`Failed: ${data.failed}`);
                    
                    // Show summary message
                    frappe.show_alert({
                        message: __(`Sync completed. ${data.succeeded} created/updated, ${data.failed} failed out of ${data.processed} documents.`),
                        indicator: 'green'
                    }, 8);
                    
                    // If we have detailed results, show them
                    show_bulk_sync_results(data);
                });
                
                frappe.realtime.on('bulk_sync_error', function(data) {
                    console.log("Received error notification:", data);
                    $progress_wrapper.find('.status').html(`Status: <span class="text-danger">Error: ${data.error}</span>`);
                    
                    frappe.show_alert({
                        message: __(`Sync failed: ${data.error}`),
                        indicator: 'red'
                    }, 5);
                });
                
                // Call method
                frm.call({
                    method: 'trigger_bulk_sync',
                    doc: frm.doc,
                    args: {
                        source_doctype: values.doctype,
                        filters: filters,
                        limit: values.limit
                    },
                    callback: function(r) {
                        console.log("Bulk sync initiated, response:", r);
                        
                        if (r.message && r.message.success) {
                            if (r.message.job_id) {
                                // It's a background job
                                $progress_wrapper.find('.status').text('Status: Processing in background...');
                                $progress_wrapper.find('.processed').text(`Processed: 0/${r.message.total_docs}`);
                                
                                // Update background notification
                                frappe.show_alert({
                                    message: __(`Bulk sync started in background for ${r.message.total_docs} documents.`),
                                    indicator: 'blue'
                                }, 8);
                            } else if (r.message.results) {
                                // Direct processing completed (smaller batch)
                                const results = r.message.results;
                                
                                // Update the UI
                                $progress_wrapper.find('.progress-bar').css('width', '100%');
                                $progress_wrapper.find('.processed').text(`Processed: ${results.processed}/${results.total}`);
                                $progress_wrapper.find('.created').text(`Created/Updated: ${results.succeeded}`);
                                $progress_wrapper.find('.failed').text(`Failed: ${results.failed}`);
                                $progress_wrapper.find('.status').text('Status: Completed');
                                
                                // Show success message
                                frappe.msgprint({
                                    title: __('Success'),
                                    indicator: 'green',
                                    message: r.message.message
                                });
                                
                                // Show detailed results
                                show_bulk_sync_results(results);
                            }
                        } else {
                            // Update error in progress dialog
                            $progress_wrapper.find('.status').html(`Status: <span class="text-danger">Error</span>`);
                            $progress_wrapper.append(`<div class="mt-3 text-danger">${r.message && r.message.message || "Unknown error"}</div>`);
                            
                            // Show error message
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

        // Helper function to update progress UI - with debugging
        function updateProgressUI(data) {
            console.log("Updating progress UI with:", data);
            const percent = data.percent || 0;
            const $progress_dialogs = $(".modal-dialog:visible").find(".sync-progress");
            
            console.log("Found progress dialogs:", $progress_dialogs.length);
            
            if ($progress_dialogs.length) {
                $progress_dialogs.each(function() {
                    const $progress = $(this);
                    $progress.find('.progress-bar').css('width', `${percent}%`);
                    $progress.find('.processed').text(`Processed: ${data.processed}/${data.total}`);
                    $progress.find('.created').text(`Created/Updated: ${data.succeeded}`);
                    $progress.find('.failed').text(`Failed: ${data.failed}`);
                    console.log("Updated progress UI elements");
                });
            } else {
                console.log("No progress dialogs found to update");
            }
        }
        
        // Add check sync status button (renamed to 'View Running Jobs')
        frm.add_custom_button(__('View Running Jobs'), function() {
            // Call the server to get list of running jobs
            frappe.call({
                method: 'core.agnikul_core_erp.doctype.live_sync.live_sync.get_bulk_sync_jobs',
                args: {
                    sync_config: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        const jobs = r.message.jobs || [];
                        
                        if (jobs.length === 0) {
                            frappe.msgprint({
                                title: __('No Running Jobs'),
                                message: __('There are no running or recent sync jobs for this configuration.'),
                                indicator: 'blue'
                            });
                            return;
                        }
                        
                        // Create a dialog to show the list of jobs
                        const d = new frappe.ui.Dialog({
                            title: __('Sync Jobs Status'),
                            fields: [
                                {
                                    fieldname: 'jobs_html',
                                    fieldtype: 'HTML'
                                }
                            ],
                            primary_action_label: __('Refresh'),
                            primary_action: function() {
                                // Refresh the job list
                                frm.trigger('view_running_jobs');
                            },
                            secondary_action_label: __('Close'),
                            secondary_action: function() {
                                d.hide();
                            }
                        });
                        
                        // Create HTML for the jobs list
                        const $jobs_wrapper = d.fields_dict.jobs_html.$wrapper;
                        let html = '<div class="jobs-list" style="color: var(--text-color);">';
                        
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
                        jobs.forEach(function(job) {
                            const start_time = job.start_time ? frappe.datetime.str_to_user(job.start_time) : '';
                            const status_class = job.status === 'Completed' ? 'text-success' : 
                                                (job.status === 'Error' ? 'text-danger' : 'text-primary');
                            
                            html += '<tr>';
                            html += '<td>' + start_time + '</td>';
                            html += '<td class="' + status_class + '">' + job.status + '</td>';
                            html += '<td>';
                            
                            // Add progress bar
                            const percent = job.percent || 0;
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
                        });
                        
                        html += '</tbody></table>';
                        html += '</div>';
                        
                        // Set the HTML and show the dialog
                        $jobs_wrapper.html(html);
                        d.show();
                        
                        // Add click handler for the view details button
                        $jobs_wrapper.find('.view-job-details').on('click', function() {
                            const jobId = $(this).data('job-id');
                            // Get job details and show them
                            frappe.call({
                                method: 'core.agnikul_core_erp.doctype.live_sync.live_sync.get_bulk_sync_job_status',
                                args: {
                                    job_id: jobId
                                },
                                callback: function(r) {
                                    if (r.message && r.message.success) {
                                        // Show the results using our existing function
                                        show_bulk_sync_results(r.message.data);
                                    } else {
                                        frappe.msgprint({
                                            title: __('Job Status Error'),
                                            message: r.message.message || __('Error retrieving job status'),
                                            indicator: 'red'
                                        });
                                    }
                                }
                            });
                        });
                        
                        // Style buttons
                        d.$wrapper.find('.btn-primary, .btn-secondary').addClass('btn-fill');
                        
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message ? r.message.message : __('Error retrieving jobs list'),
                            indicator: 'red'
                        });
                    }
                }
            });
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

// Helper function to update progress UI
function updateProgressUI(data) {
    const percent = data.percent || 0;
    const $progress_dialogs = $(".modal-dialog:visible").find(".sync-progress");
    
    if ($progress_dialogs.length) {
        $progress_dialogs.each(function() {
            const $progress = $(this);
            $progress.find('.progress-bar').css('width', `${percent}%`);
            $progress.find('.processed').text(`Processed: ${data.processed}/${data.total}`);
            $progress.find('.created').text(`Created/Updated: ${data.succeeded}`);
            $progress.find('.failed').text(`Failed: ${data.failed}`);
        });
    }
}

// Function to show bulk sync results - enhanced version
function show_bulk_sync_results(results) {
    // Support both old format and new job-based format
    let html = '<div style="color: var(--text-color);">';
    
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
    
    // Add job details if available (new format)
    if (results.job_id) {
        const start_time = results.start_time ? frappe.datetime.str_to_user(results.start_time) : '';
        const end_time = results.end_time ? frappe.datetime.str_to_user(results.end_time) : '';
        
        // Calculate duration if possible
        let duration = '';
        if (results.start_time && results.end_time) {
            const start = moment(results.start_time);
            const end = moment(results.end_time);
            const diff = moment.duration(end.diff(start));
            duration = `${Math.floor(diff.asMinutes())}m ${diff.seconds()}s`;
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
    
    // Add error message if present
    if (results.error) {
        html += '<div class="error-section mt-3">';
        html += '<div class="alert alert-danger">';
        html += '<strong>' + __('Error') + ':</strong> ' + results.error;
        html += '</div>';
        html += '</div>';
    }
    
    html += '</div>'; // Close main container
    
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

function open_sync_config_dialog(frm) {
    const src = frm.doc.source_doctype;
    const tgt = frm.doc.target_doctype;
    if (!src || !tgt) {
        frappe.msgprint(__('Please set both Source and Target DocTypes first.'));
        return;
    }
    frappe.model.with_doctype(src, () => frappe.model.with_doctype(tgt, () => {
        const src_meta = frappe.get_meta(src);
        const tgt_meta = frappe.get_meta(tgt);

        // Field lists
        const field_options = fmeta => fmeta.fields.map(f => f.fieldname + ' [' + f.fieldtype + ']');
        const source_fields = field_options(src_meta);
        const target_fields = field_options(tgt_meta);

        const d = new frappe.ui.Dialog({
            title: __('Configure Sync Configuration'),
            size: 'large',
            fields: [
                { fieldtype: 'HTML', fieldname: 'beta_info', options: '<p><em>Use this form to manage all sync settings.</em></p>' },
                { fieldtype: 'Table', fieldname: 'direct_fields', label: __('Direct Field Mappings'), in_place: true,
                  cannot_add_rows: false, data: [{'source_field':'', 'target_field':''}],
                  fields: [
                      { fieldtype: 'Select', fieldname: 'source_field', label: __('Source Field'), options: source_fields, reqd:1, "in_list_view": 1 },
                      { fieldtype: 'Select', fieldname: 'target_field', label: __('Target Field'), options: target_fields, reqd:1, "in_list_view": 1 }
                  ]
                },
                { fieldtype: 'Table', fieldname: 'child_mappings', label: __('Child Table Mappings'), in_place: true,
                  cannot_add_rows: false, data: [{'source_table':'', 'target_table':'', 'fields_map':''}],
                  fields: [
                      { fieldtype: 'Data',   fieldname: 'source_table', label: __('Source Table'), reqd:1, "in_list_view": 1 },
                      { fieldtype: 'Data',   fieldname: 'target_table', label: __('Target Table'), reqd:1, "in_list_view": 1 },
                      { fieldtype: 'Small Text', fieldname:'fields_map', label: __('Field Map (JSON)'), reqd:1, "in_list_view": 1 }
                  ]
                },
                { fieldtype: 'Table', fieldname: 'default_values', label: __('Default Values'), in_place: true,
                  cannot_add_rows: false, data: [{'fieldname':'', 'default_value':''}],
                  fields: [
                      { fieldtype: 'Select', fieldname: 'fieldname', label: __('Field'), options: target_fields, reqd:1, "in_list_view": 1 },
                      { fieldtype: 'Data',   fieldname: 'default_value', label: __('Default Value'), reqd:1, "in_list_view": 1 }
                  ]
                },
                { fieldtype: 'Table', fieldname: 'transforms', label: __('Transforms'), in_place: true,
                  cannot_add_rows: false, data: [{'fieldname':'', 'function_path':''}],
                  fields: [
                      { fieldtype: 'Select', fieldname: 'fieldname', label: __('Source Field'), options: source_fields, reqd:1, "in_list_view": 1 },
                      { fieldtype: 'Data',   fieldname: 'function_path', label: __('Transform Function Path'), reqd:1, "in_list_view": 1, }
                  ]
                },
                { fieldtype: 'Section Break' },
                { fieldtype: 'Data', fieldname: 'hooks_before', label: __('Before Sync Hook (Function Path)') },
                { fieldtype: 'Data', fieldname: 'hooks_after',  label: __('After Sync Hook (Function Path)') },
                { fieldtype: 'Check', fieldname: 'allow_recreate', label: __('Allow Recreate Deleted Targets') },
                { fieldtype: 'Button', fieldname: 'save', label: __('Save Configuration'), btnType:'btn-primary' }
            ]
        });

        // Load existing
        let cfg = {};
        try { cfg = frm.doc.config ? JSON.parse(frm.doc.config) : {}; } catch(_) {}
        d.set_value('direct_fields', Object.entries(cfg.direct_fields||{}).map(([s,t])=>({source_field:s, target_field:t})) || []);
        d.set_value('child_mappings', (cfg.child_mappings||[]).length ?
            cfg.child_mappings.map(m=>({source_table:m.source_table,target_table:m.target_table,fields_map:JSON.stringify(m.fields)})) :
            []
        );
        d.set_value('default_values', Object.entries(cfg.default_values||{}).map(([f,v])=>({fieldname:f, default_value:v})) || []);
        d.set_value('transforms', Object.entries(cfg.transform||{}).map(([f,p])=>({fieldname:f, function_path:p})) || []);
        d.set_value('hooks_before', cfg.hooks?.before_sync);
        d.set_value('hooks_after', cfg.hooks?.after_sync);
        d.set_value('allow_recreate', cfg.allow_recreate===false?0:1);

        // Save handler
        d.fields_dict.save.$input.on('click', () => {
            const newcfg = { direct_fields:{}, child_mappings:[], default_values:{}, transform:{}, hooks:{}, allow_recreate:true };
            const vals = d.get_values();
            (vals.direct_fields||[]).forEach(r=>{ newcfg.direct_fields[r.source_field]=r.target_field; });
            (vals.child_mappings||[]).forEach(r=>{
                try { newcfg.child_mappings.push({ source_table:r.source_table, target_table:r.target_table, fields:JSON.parse(r.fields_map) }); }
                catch(e){ frappe.msgprint({message:__('Invalid JSON in child fields'),indicator:'red'}); return; }
            });
            (vals.default_values||[]).forEach(r=>{ newcfg.default_values[r.fieldname]=r.default_value; });
            (vals.transforms||[]).forEach(r=>{ newcfg.transform[r.fieldname]=r.function_path; });
            newcfg.hooks.before_sync = vals.hooks_before;
            newcfg.hooks.after_sync  = vals.hooks_after;
            newcfg.allow_recreate = !!vals.allow_recreate;
            frm.set_value('config', JSON.stringify(newcfg, null, 4));
            d.hide();
        });

        d.show();
    }));
}
