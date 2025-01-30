from __future__ import unicode_literals, absolute_import
import os
import json
import click
import frappe
from datetime import datetime
import sys
import traceback
import importlib.util

from termcolor import colored

def get_doctype_module(doctype):
    
    try:
        module = frappe.get_list("DocType", 
            filters={"name": doctype}, 
            fields=["module"],
            limit=1
        )
        
        return module[0].get('module') if module else None
    except Exception as e:
        click.echo(colored(f"Error finding module for doctype {doctype}: {e}", 'black', 'on_red'))
        return None

def prepare_sql_insert(table_name, data):
    
    # Remove None values and child_tables
    data = {k: v for k, v in data.items() if v is not None and k != 'child_tables'}
    
    columns = ', '.join([f"`{col}`" for col in data.keys()])
    placeholders = ', '.join(['%s'] * len(data))
    values = tuple(data.values())
    
    query = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"
    return query, values

def restore_documents(docs, doctype, verbose=False):
    
    restored_count = 0
    
    # Determine table names
    parent_table = f"tab{doctype}"
    
    # Restore parent documents
    for doc in docs:
        try:
            # Prepare parent document data
            parent_doc = doc.copy()
            
            # Prepare SQL insert
            insert_query, insert_values = prepare_sql_insert(parent_table, parent_doc)
            
            try:
                # Execute direct SQL insert
                frappe.db.sql(insert_query, insert_values)
                
                restored_count += 1
                
                if verbose:
                    click.echo(colored(f"Restored parent document: {doc.get('name')}", 'green'))
            
            except Exception as insert_error:
                if verbose:
                    click.echo(colored(f"Error inserting parent document: {insert_error}", 'black', 'on_red'))
        
        except Exception as e:
            if verbose:
                click.echo(colored(f"Error processing parent document: {e}", 'black', 'on_red'))
    
    return restored_count

@click.command('restore-app')
@click.option('--site', default=None, type=str, help='Specify the site name (optional). If not provided, uses the current site.')
@click.option('--verbose', is_flag=True, help='Enable verbose logging for detailed troubleshooting.')
@click.argument('appname', type=str)
@click.argument('backup_path', default=None, required=False, type=str)
def restore_app(site, verbose, appname, backup_path=None):
    """
    Restore documents for a specific app from a backup.
    
    This command restores all documents for the specified app from a backup.
    It supports:
    - Automatic selection of the most recent backup if no path is specified
    - Optional verbose logging for detailed troubleshooting
    - Site-specific restoration
    
    Restoration process:
    1. Locates the backup directory or specified backup path
    2. Clears existing documents for each doctype in the app
    3. Restores documents from the backup JSON files
    4. Commits changes to the database
    
    Backup location searched: ./backup/<appname>/
    
    Examples:
    \b
    - bench restore-app core
    - bench restore-app core --site mysite
    - bench restore-app core --verbose
    - bench restore-app core /path/to/specific/backup
    """
    # Determine the site
    if not site:
        try:
            with open('currentsite.txt', 'r') as f:
                site = f.read().strip()
        except FileNotFoundError:
            click.echo(colored("Error: currentsite.txt not found and no --site provided.", 'black', 'on_red'))
            return

    # Initialize Frappe and connect to the site
    try:
        frappe.init(site=site)
        frappe.connect()
    except Exception as e:
        click.echo(colored(f"Error initializing Frappe for site '{site}': {e}", 'black', 'on_red'))
        return

    # Find the backup path
    if not backup_path:
        backup_dir = os.path.join('backup', appname)
        if not os.path.exists(backup_dir):
            click.echo(colored(f"No backup directory found for app '{appname}'", 'black', 'on_red'))
            frappe.destroy()
            return

        # Find the most recent backup
        backups = [d for d in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, d))]
        if not backups:
            click.echo(colored(f"No backups found for app '{appname}'", 'black', 'on_red'))
            frappe.destroy()
            return
        
        backup_path = os.path.join(backup_dir, max(backups))

    # Validate backup path
    if not os.path.exists(backup_path):
        click.echo(colored(f"Backup path does not exist: {backup_path}", 'black', 'on_red'))
        frappe.destroy()
        return

    # Fetch all JSON files in the backup directory
    backup_files = [f for f in os.listdir(backup_path) if f.endswith('.json')]

    # Restore documents for each doctype
    for backup_file in backup_files:
        doctype = backup_file.replace('.json', '')
        try:
            # Read the backup file
            with open(os.path.join(backup_path, backup_file), 'r') as f:
                parent_docs = json.load(f)

            # Find the module for the doctype
            module = get_doctype_module(doctype)
            if not module:
                click.echo(colored(f"Warning: Could not find module for doctype '{doctype}'. Skipping.", 'yellow'))
                continue

            # Clear existing documents for the doctype before restoring
            frappe.db.delete(doctype)

            # Restore documents with direct SQL
            restored_count = restore_documents(parent_docs, doctype, verbose)

            print(f"Restored {restored_count} documents for doctype '{doctype}'")

        except Exception as e:
            click.echo(colored(f"Error processing doctype '{doctype}': {e}", 'black', 'on_red'))
            # Print full traceback for debugging
            import traceback
            traceback.print_exc()

    # Commit changes
    frappe.db.commit()
    frappe.destroy()
    click.echo(colored(f"Restore completed for app '{appname}' from {backup_path}", 'black', 'on_green'))

commands = [restore_app]
