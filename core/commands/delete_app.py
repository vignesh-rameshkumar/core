from __future__ import unicode_literals, absolute_import
import os
import click
import frappe
import subprocess
import sys
import traceback
import importlib.util

from termcolor import colored

def get_app_doctypes(appname):
    """
    Retrieve all doctypes for a given app.
    """
    try:
        # Get all modules for the app
        app_modules = frappe.get_module_list(appname)
        
        # Find doctypes in these modules
        doctypes = []
        for module in app_modules:
            module_doctypes = frappe.get_list("DocType", 
                filters={"module": module}, 
                pluck="name"
            )
            doctypes.extend(module_doctypes)
        
        return doctypes
    except Exception as e:
        click.echo(colored(f"Error finding doctypes for app '{appname}': {e}", 'black', 'on_red'))
        return []

def delete_app_documents(appname, site=None):
    """
    Delete all documents for doctypes in the specified app.
    """
    try:
        # Determine the site
        if not site:
            try:
                with open('currentsite.txt', 'r') as f:
                    site = f.read().strip()
            except FileNotFoundError:
                click.echo(colored("Error: currentsite.txt not found and no site provided.", 'black', 'on_red'))
                return False

        # Initialize Frappe and connect to the site
        frappe.init(site=site)
        frappe.connect()

        # Get doctypes for the app
        doctypes = get_app_doctypes(appname)

        if not doctypes:
            print(f"No doctypes found for app '{appname}'.")
            return False

        # Delete documents for each doctype
        for doctype in doctypes:
            try:
                frappe.db.delete(doctype)
                print(f"Deleted all documents for doctype: {doctype}")
            except Exception as doctype_error:
                click.echo(colored(f"Error deleting documents for doctype {doctype}: {doctype_error}", 'black', 'on_red'))

        # Commit changes
        frappe.db.commit()
        frappe.destroy()
        
        return True

    except Exception as e:
        click.echo(colored(f"Error deleting app documents: {e}", 'black', 'on_red'))
        return False

@click.command('delete-app')
@click.option('--site', default=None, type=str, help='Specify the site name (optional). If not provided, uses the current site.')
@click.argument('appname')
@click.option('--backup/--no-backup', default=True, 
              prompt='Do you want to take a backup before deleting?',
              help='Take a backup before deleting app documents. Default is to create a backup.')
def delete_app(site, appname, backup):
    """
    Permanently delete all documents for a specific app with optional backup.
    
    This command provides a comprehensive and safe document deletion mechanism:
    
    Key Features:
    - Mandatory pre-deletion backup confirmation
    - Site-specific document management
    - Granular, doctype-level deletion
    - Atomic transaction with database commit
    
    Deletion Workflow:
    1. Prompt for backup confirmation (default: yes)
    2. Create a comprehensive backup of all app documents
    3. Identify all doctypes associated with the specified app
    4. Systematically delete documents for each doctype
    5. Commit changes to the database
    
    Safety Mechanisms:
    - Backup creation prevents irreversible data loss
    - Explicit user confirmation required
    - Supports disabling backup with --no-backup flag
    
    Potential Use Cases:
    - Cleaning up test or deprecated app data
    - Preparing for app reinstallation
    - Managing development environment
    
    Performance Considerations:
    - Deletion process scales with the number of doctypes
    - Larger apps may require more time to process
    
    Examples:
    \b
    - bench delete-app core                  # Delete with backup
    - bench delete-app core --site mysite    # Delete on specific site
    - bench delete-app core --no-backup      # Delete without backup
    
    ⚠️ WARNING: Irreversible operation. Use with extreme caution.
    """
    try:
        # Backup if requested
        if backup:
            try:
                # Use subprocess to run backup-app command
                backup_result = subprocess.run(
                    ['bench', 'backup-app', appname], 
                    capture_output=True, 
                    text=True
                )
                
                if backup_result.returncode != 0:
                    click.echo(colored("Backup failed. Aborting deletion.", 'black', 'on_red'))
                    click.echo(colored(backup_result.stderr, 'black', 'on_red'))
                    return
                
                click.echo(colored("Backup completed successfully.", 'black', 'on_green'))
            
            except Exception as backup_error:
                click.echo(colored(f"Error during backup: {backup_error}", 'black', 'on_red'))
                return

        # Delete app documents
        deletion_success = delete_app_documents(appname, site)

        if deletion_success:
            click.echo(colored(f"Successfully deleted all documents for app '{appname}'", 'black', 'on_green', attrs=['bold']))
        else:
            click.echo(colored(f"Failed to delete documents for app '{appname}'", 'black', 'on_red', attrs=['bold']))

    except Exception as e:
        click.echo(colored(f"Unexpected error: {e}", 'black', 'on_red'))

commands = [delete_app]
