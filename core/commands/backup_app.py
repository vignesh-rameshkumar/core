from __future__ import unicode_literals, absolute_import
import os
import json
import click
import frappe
from datetime import datetime
import sys
import traceback
import importlib.util

try:
    from termcolor import colored
except ImportError as e:
    print(f"Import Error for termcolor: {e}")
    print("Python Path:", sys.path)
    traceback.print_exc()
    
    # Attempt to import using full path
    try:
        termcolor_path = '/home/vignesh/.local/lib/python3.10/site-packages/termcolor/__init__.py'
        spec = importlib.util.spec_from_file_location("termcolor", termcolor_path)
        termcolor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(termcolor)
        colored = termcolor.colored
    except Exception as fallback_error:
        print(f"Fallback import failed: {fallback_error}")
        colored = lambda text, color=None, attrs=None: text  # Fallback dummy function

def get_all_doctypes(appname):
    
    try:
        app_modules = frappe.get_module_list(appname)
        doctypes = []
        for module in app_modules:
            module_doctypes = frappe.get_list("DocType", filters={"module": module}, pluck="name")
            doctypes.extend(module_doctypes)
        return doctypes
    except Exception as e:
        raise Exception(f"Failed to retrieve doctypes: {e}")

def json_datetime_handler(obj):
    
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@click.command('backup-app')
@click.option('--site', default=None, type=str, help='Specify the site name (optional). If not provided, uses the current site.')
@click.argument('appname', type=str)
def backup_app(site, appname):
    """
    Create a comprehensive backup of all documents for a specific app.
    
    This command provides a robust backup mechanism that:
    
    Features:
    - Creates a timestamped backup directory for each backup
    - Captures all documents for each doctype in the specified app
    - Preserves document hierarchy, including parent and child documents
    - Supports site-specific backups
    
    Backup process:
    1. Identifies all doctypes associated with the app
    2. Retrieves parent and child documents for each doctype
    3. Saves documents in JSON format, maintaining original structure
    4. Organizes backups in a chronological directory structure
    
    Backup location: ./backup/<appname>/<timestamp>/
    
    Each backup includes:
    - Separate JSON files for each doctype
    - Complete document data, including nested child documents
    - Timestamp-based versioning
    
    Examples:
    \b
    - bench backup-app core                  # Backup core app on current site
    - bench backup-app core --site mysite    # Backup core app on specific site
    
    Caution: Ensure sufficient disk space before creating large backups.
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

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_dir = os.path.join('backup', appname, timestamp)
    os.makedirs(backup_dir, exist_ok=True)

    # Fetch all doctypes for the app
    try:
        doctypes = get_all_doctypes(appname)
    except Exception as e:
        click.echo(colored(f"Error fetching doctypes for app '{appname}': {e}", 'black', 'on_red'))
        frappe.destroy()
        return

    # Backup documents for each doctype
    for doctype in doctypes:
        try:
            # Fetch parent documents
            parent_docs = frappe.get_all(doctype, fields=["*"])
            
            # Fetch child documents for each parent
            for parent_doc in parent_docs:
                # Find child tables for this doctype
                child_tables = frappe.get_list("DocField", 
                    filters={
                        "parent": doctype, 
                        "fieldtype": "Table"
                    }, 
                    pluck="options"
                )
                
                # Backup child documents for each child table
                parent_doc['child_tables'] = {}
                for child_table in child_tables:
                    child_docs = frappe.get_all(child_table, 
                        filters={"parenttype": doctype, "parent": parent_doc['name']},
                        fields=["*"]
                    )
                    parent_doc['child_tables'][child_table] = child_docs

            # Save parent documents with their child documents to JSON file
            backup_file = os.path.join(backup_dir, f"{doctype}.json")
            with open(backup_file, 'w') as f:
                json.dump(parent_docs, f, indent=4, default=json_datetime_handler)
        
        except Exception as e:
            click.echo(colored(f"Error backing up doctype '{doctype}': {e}", 'black', 'on_red'))

    frappe.destroy()
    click.echo(colored(f"Backup completed for app '{appname}' at {backup_dir}", 'black', 'on_green'))

commands = [backup_app]
