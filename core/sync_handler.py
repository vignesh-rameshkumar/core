import frappe
import json

def process_doc_event(doc, event):
    """Process document events for sync with optimized performance"""
    # Skip if already syncing or if Live Sync DocType doesn't exist
    if hasattr(doc, "_syncing") and doc._syncing:
        return
        
    # Skip system doctypes to avoid unnecessary processing
    if doc.doctype in ["Live Sync", "Sync Log", "Error Log", "Activity Log"]:
        return
        
    # Check cache first for sync configs (avoid DB query if possible)
    cache_key = f"sync_configs_for_{doc.doctype}"
    cached = frappe.cache().get_value(cache_key)
    
    if cached is None:
        # Only check database if needed
        if not frappe.db.exists('DocType', 'Live Sync'):
            # Cache empty result to avoid repeated checks
            frappe.cache().set_value(cache_key, "[]", expires_in_sec=3600)
            return
            
        configs = get_sync_configs_for_doctype(doc.doctype)
        if not configs:
            return
    else:
        configs = json.loads(cached)
        if not configs:  # Empty list in cache
            return
        
    # Process each configuration
    for config_name in configs:
        try:
            # Use cached doc to avoid repeated loading of the same configuration
            config = frappe.get_cached_doc("Live Sync", config_name)
            
            # Skip if not enabled
            if not config.enabled:
                continue
                
            # Determine sync direction
            is_forward = (doc.doctype == config.source_doctype)
            
            # Process sync
            config.sync_document(doc, event, is_forward)
        except Exception as e:
            frappe.log_error(f"Sync error for {doc.doctype} {doc.name}: {str(e)}", "LiveSync Handler Error")
            
def get_sync_configs_for_doctype(doctype):
    """Get sync configs for a doctype using optimized query and caching"""
    # Check cache first
    cache_key = f"sync_configs_for_{doctype}"
    cached = frappe.cache().get_value(cache_key)
    
    if cached:
        return json.loads(cached)
        
    try:
        # Optimized single query instead of two separate queries
        configs = frappe.db.sql("""
            SELECT name FROM `tabLive Sync` 
            WHERE enabled = 1
            AND (
                (source_doctype = %s)
                OR (target_doctype = %s AND bidirectional = 1)
            )
        """, (doctype, doctype), as_dict=0)
        
        # Extract names from query result
        result = [c[0] for c in configs]
        
        # Cache for 30 minutes (sync config changes are infrequent)
        frappe.cache().set_value(cache_key, json.dumps(result), expires_in_sec=1800)
        
        return result
    except Exception as e:
        frappe.log_error(f"Error getting sync configs: {str(e)}", "LiveSync Error")
        return []
    
def clear_sync_cache():
    """Clear sync cache more selectively"""
    # Only clear for DocTypes with active sync configurations
    sync_doctypes = set()
    
    # Get all enabled sync configurations
    configs = frappe.db.sql("""
        SELECT source_doctype, target_doctype 
        FROM `tabLive Sync` 
        WHERE enabled = 1
    """, as_dict=1)
    
    for config in configs:
        sync_doctypes.add(config.source_doctype)
        sync_doctypes.add(config.target_doctype)
    
    # Clear cache only for relevant DocTypes
    for dt in sync_doctypes:
        frappe.cache().delete_value(f"sync_configs_for_{dt}")
        
@frappe.whitelist()
def process_bulk_sync(sync_config, source_doctype, doc_names, is_forward, job_id=None, fast_mode=0):
    """
    Process bulk sync in background with optimized performance
    
    Args:
        sync_config: Name of LiveSync configuration
        source_doctype: DocType to sync from
        doc_names: List of document names to sync
        is_forward: Direction of sync
        job_id: Job ID for tracking progress
        fast_mode: If 1, bypasses validations and hooks for performance
    """
    try:
        # Get sync configuration
        sync = frappe.get_cached_doc("Live Sync", sync_config)
        
        # Initialize counters
        total = len(doc_names)
        processed = 0
        succeeded = 0
        failed = 0
        details = []
        
        # Create job ID if not provided
        if not job_id:
            import uuid
            job_id = f"bulk_sync_{uuid.uuid4().hex[:8]}"
        
        # Cache key for job data
        cache_key = f"bs:{job_id}"
        
        # Initial job data
        job_data = {
            "total": total,
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "status": "In Progress",
            "start_time": frappe.utils.now(),
            "sync_config": sync_config,
            "source_doctype": source_doctype,
            "direction": "Forward" if is_forward else "Backward",
            "percent": 0
        }
        
        # Store initial job data
        frappe.cache().set_value(cache_key, json.dumps(job_data), expires_in_sec=3600)
        
        # Initial progress notification
        frappe.publish_realtime(
            event='bulk_sync_progress',
            message={
                'job_id': job_id,
                'percent': 0,
                'processed': 0,
                'total': total,
                'succeeded': 0,
                'failed': 0,
                'sync_config': sync_config
            },
            after_commit=True
        )
        
        # Fast mode implementation
        if fast_mode:
            # Process using direct DB operations
            results = sync._process_bulk_sync_fast_mode(
                source_doctype, doc_names, is_forward
            )
            
            # Update final status
            final_data = {
                "processed": results["processed"],
                "succeeded": results["succeeded"],
                "failed": results["failed"],
                "percent": 100,
                "status": "Completed",
                "end_time": frappe.utils.now(),
                "details": results["details"][:50]  # Limit details to avoid cache bloat
            }
            
            frappe.cache().set_value(cache_key, json.dumps({**job_data, **final_data}), expires_in_sec=3600)
            
            # Send completion notification
            frappe.publish_realtime(
                event='bulk_sync_completed',
                message={
                    'job_id': job_id,
                    'processed': results["processed"],
                    'succeeded': results["succeeded"], 
                    'failed': results["failed"],
                    'sync_config': sync_config
                },
                after_commit=True
            )
            
            return
        
        # Determine optimal batch size - smaller for larger jobs to show progress
        batch_size = 25
        if total > 500:
            batch_size = 50
        elif total < 100:
            batch_size = 10
            
        # Calculate update frequency - less frequent updates for larger jobs
        update_frequency = max(batch_size // 2, 5)
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = doc_names[i:i+batch_size]
            
            for doc_name in batch:
                try:
                    # Get full document
                    doc = frappe.get_doc(source_doctype, doc_name)
                    
                    # Process sync
                    sync.sync_document(doc, "on_update", is_forward)
                    
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
                
                # Update progress periodically
                if processed % update_frequency == 0 or processed == total:
                    # Calculate percentage
                    percent = int((processed / total) * 100)
                    
                    # Update cache with current progress
                    update_data = {
                        "processed": processed,
                        "succeeded": succeeded,
                        "failed": failed,
                        "percent": percent
                    }
                    
                    frappe.cache().set_value(cache_key, json.dumps({**job_data, **update_data}), expires_in_sec=3600)
                    
                    # Send progress update
                    frappe.publish_realtime(
                        event='bulk_sync_progress',
                        message={
                            'job_id': job_id,
                            'percent': percent,
                            'processed': processed,
                            'total': total,
                            'succeeded': succeeded,
                            'failed': failed,
                            'sync_config': sync_config
                        },
                        after_commit=True
                    )
            
            # Commit after each batch
            frappe.db.commit()
        
        # Update last sync timestamp
        last_key = 'last_synced_forward' if is_forward else 'last_synced_backward'
        sync.db_set(last_key, frappe.utils.now_datetime(), update_modified=False)
        
        # Final update
        final_data = {
            "status": "Completed",
            "end_time": frappe.utils.now(),
            "percent": 100,
            "details": details[:50]  # Limit details stored in cache
        }
        
        frappe.cache().set_value(cache_key, json.dumps({**job_data, **update_data, **final_data}), expires_in_sec=3600)
        
        # Send completion notification
        frappe.publish_realtime(
            event='bulk_sync_completed',
            message={
                'job_id': job_id,
                'processed': processed,
                'succeeded': succeeded, 
                'failed': failed,
                'sync_config': sync_config
            },
            after_commit=True
        )
        
    except Exception as e:
        # Update job status on error
        if job_id:
            error_data = {
                "status": "Error",
                "error": str(e),
                "end_time": frappe.utils.now()
            }
            
            current_data = json.loads(frappe.cache().get_value(cache_key) or "{}")
            frappe.cache().set_value(cache_key, json.dumps({**current_data, **error_data}), expires_in_sec=3600)
            
            # Send error notification
            frappe.publish_realtime(
                event='bulk_sync_error',
                message={
                    'job_id': job_id,
                    'error': str(e),
                    'sync_config': sync_config
                },
                after_commit=True
            )
        
        frappe.log_error(f"Bulk sync error: {str(e)}", "Bulk Sync Error")

@frappe.whitelist()
def get_bulk_sync_jobs(sync_config=None):
    """Get the list of bulk sync jobs for a configuration"""
    try:
        # Get recent Sync Logs
        log_filters = {}
        if sync_config:
            log_filters["sync_configuration"] = sync_config
            
        # Find recent logs grouped by day
        recent_logs = frappe.db.sql("""
            SELECT 
                sync_configuration, 
                DATE(timestamp) as sync_date,
                source_doctype, 
                target_doctype,
                direction,
                MIN(timestamp) as start_time,
                MAX(timestamp) as end_time,
                COUNT(*) as processed,
                SUM(CASE WHEN status = 'Success' THEN 1 ELSE 0 END) as succeeded,
                SUM(CASE WHEN status != 'Success' THEN 1 ELSE 0 END) as failed
            FROM `tabSync Log`
            WHERE timestamp > DATE_SUB(NOW(), INTERVAL 7 DAY)
            {where_condition}
            GROUP BY sync_configuration, DATE(timestamp), source_doctype, target_doctype, direction
            ORDER BY sync_date DESC, start_time DESC
            LIMIT 20
        """.format(
            where_condition = f"AND sync_configuration = '{sync_config}'" if sync_config else ""
        ), as_dict=1)
        
        # Format results as jobs
        jobs = []
        for log in recent_logs:
            job_id = f"{log.sync_configuration}:{log.sync_date}:{log.source_doctype}"
            
            # Calculate percent
            percent = 0
            if log.processed > 0:
                percent = round((log.succeeded / log.processed) * 100, 2)
                
            jobs.append({
                "job_id": job_id,
                "sync_config": log.sync_configuration,
                "source_doctype": log.source_doctype,
                "target_doctype": log.target_doctype,
                "direction": log.direction,
                "start_time": log.start_time,
                "end_time": log.end_time,
                "status": "Completed",
                "processed": log.processed,
                "succeeded": log.succeeded,
                "failed": log.failed,
                "total": log.processed,
                "percent": percent
            })
            
        # Check for active background jobs in cache
        if sync_config:
            active_jobs = []
            for key in frappe.cache().get_keys(f"bs:bulk_sync_*"):
                job_data = frappe.cache().get_value(key)
                if job_data:
                    try:
                        job = json.loads(job_data)
                        if job.get("sync_config") == sync_config and job.get("status") != "Completed":
                            job["job_id"] = key.split(':')[1]  # Extract job_id from key
                            active_jobs.append(job)
                    except:
                        pass
                        
            # Combine with database results
            jobs = active_jobs + jobs
            
        return {
            "success": True,
            "jobs": jobs
        }
    except Exception as e:
        frappe.log_error(f"Error getting jobs list: {str(e)}", "Bulk Sync Jobs Error")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def get_bulk_sync_job_status(job_id):
    """Get the status of a bulk sync job"""
    try:
        # Check if this is a background job
        cache_key = f"bs:{job_id}"
        job_data = frappe.cache().get_value(cache_key)
        
        if job_data:
            # Return cached job data
            return {
                "success": True,
                "data": json.loads(job_data)
            }
            
        # If not found in cache, it might be a historical job
        # Parse job_id to extract components
        try:
            parts = job_id.split(':')
            if len(parts) >= 3:
                sync_config = parts[0]
                sync_date = parts[1]
                source_doctype = parts[2]
                
                # Query logs for this job
                logs = frappe.db.sql("""
                    SELECT 
                        sync_configuration, 
                        source_doctype,
                        source_doc,
                        status,
                        event,
                        timestamp
                    FROM `tabSync Log`
                    WHERE sync_configuration = %s
                    AND DATE(timestamp) = %s
                    AND source_doctype = %s
                    ORDER BY timestamp DESC
                    LIMIT 50
                """, (sync_config, sync_date, source_doctype), as_dict=1)
                
                if logs:
                    # Count stats
                    processed = len(logs)
                    succeeded = sum(1 for log in logs if log.status == 'Success')
                    failed = processed - succeeded
                    
                    # Extract details
                    details = []
                    for log in logs:
                        details.append({
                            "name": log.source_doc,
                            "status": "Success" if log.status == 'Success' else "Failed"
                        })
                    
                    # Create job data
                    job_data = {
                        "job_id": job_id,
                        "sync_config": sync_config,
                        "source_doctype": source_doctype,
                        "start_time": min(log.timestamp for log in logs),
                        "end_time": max(log.timestamp for log in logs),
                        "status": "Completed",
                        "processed": processed,
                        "succeeded": succeeded,
                        "failed": failed,
                        "total": processed,
                        "percent": 100,
                        "details": details
                    }
                    
                    return {
                        "success": True,
                        "data": job_data
                    }
        except:
            pass
                
        # Job not found
        return {
            "success": False,
            "message": "Job not found or expired"
        }
    except Exception as e:
        frappe.log_error(f"Error getting job status: {str(e)}", "Bulk Sync Job Status Error")
        return {
            "success": False,
            "message": str(e)
        }