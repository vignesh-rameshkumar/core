from __future__ import unicode_literals, absolute_import
import os
import json
import click
import frappe
from datetime import datetime
from termcolor import colored

@click.command('restore-doctype')
@click.option('--site', default=None, type=str, help='Specify the site name (optional). If not provided, uses the current site.')
@click.argument('doctype', type=str)
@click.argument('backup_file', required=False, type=str)
def restore_doctype(site, doctype, backup_file):
    """
    Restore the latest backup of a specific Doctype.

    This command:
    - Identifies the latest backup file for the specified Doctype.
    - Restores the documents from the backup file into the database.

    Examples:
    \b
    - bench restore-doctype {doctype}
    - bench restore-doctype {doctype} {filename}
    - bench restore-doctype {doctype} --site {sitename}
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

    # Locate the latest backup file
    backup_dir = os.path.join('..', 'sites', 'backup', 'doctype', doctype)
    if not os.path.exists(backup_dir):
        click.echo(colored(f"Error: Backup directory for Doctype '{doctype}' does not exist.", 'black', 'on_red'))
        frappe.destroy()
        return

    try:
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
        if not backup_files:
            click.echo(colored(f"Error: No backup files found for Doctype '{doctype}'.", 'black', 'on_red'))
            frappe.destroy()
            return

        # Use the specified backup file or pick the latest
        if backup_file:
            latest_backup_path = os.path.join(backup_dir, backup_file)
            if not os.path.exists(latest_backup_path):
                click.echo(colored(f"Error: Specified backup file '{backup_file}' does not exist.", 'black', 'on_red'))
                frappe.destroy()
                return
        else:
            latest_backup = max(backup_files, key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)))
            latest_backup_path = os.path.join(backup_dir, latest_backup)

        # Load the backup data
        with open(latest_backup_path, 'r') as f:
            documents = json.load(f)

        # Restore documents into the database
        for doc in documents:
            if frappe.db.exists(doctype, doc.get('name')):
                frappe.db.set_value(doctype, doc.get('name'), doc)
            else:
                frappe.get_doc(doc).insert()

        frappe.db.commit()
        click.echo(colored(f"Restore completed for Doctype '{doctype}' from backup '{os.path.basename(latest_backup_path)}'.", 'black', 'on_green'))
    except Exception as e:
        click.echo(colored(f"Error restoring Doctype '{doctype}': {e}", 'black', 'on_red'))
    finally:
        frappe.destroy()

commands = [restore_doctype]
