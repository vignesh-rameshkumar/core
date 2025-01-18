from __future__ import unicode_literals, absolute_import
import os
import click
import frappe
import subprocess
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
        click.echo(colored(f"Error finding doctypes for app '{appname}': {e}", 'red'))
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
                click.echo(colored("Error: currentsite.txt not found and no site provided.", 'red'))
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
                click.echo(colored(f"Deleted all documents for doctype: {doctype}", 'black', 'on_green'))
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
@click.option('--site', default=None, help='Specify the site name (optional).')
@click.argument('appname')
@click.option('--backup/--no-backup', default=True, 
              prompt='Do you want to take a backup before deleting?',
              help='Take a backup before deleting app documents.')
def delete_app(site, appname, backup):
    """
    Delete all documents for a specified app.
    Optionally takes a backup before deletion.
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
