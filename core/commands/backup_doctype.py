from __future__ import unicode_literals, absolute_import
import os
import json
import click
import frappe
from datetime import datetime, date
from termcolor import colored

def json_datetime_handler(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@click.command('backup-doctype')
@click.option('--site', default=None, type=str, help='Specify the site name (optional). If not provided, uses the current site.')
@click.argument('doctype', type=str)
@click.option('--from', 'start_date', default=None, type=str, help='Start date in YYYY-MM-DD format (optional, use --from).')
@click.option('--to', 'end_date', default=None, type=str, help='End date in YYYY-MM-DD format (optional, use --to).')
def backup_doctype(site, doctype, start_date, end_date):
    """
    Backup a specific Doctype within a given date range.

    This command:
    - Validates the given date range with the creation date of the documents.
    - Fetches documents for the specified Doctype within the date range.
    - Saves the backup in JSON format in the bench/sites/backup/Doctype folder with a timestamped filename.

    Examples:
    \b
    - bench backup-doctype User --from 2025-01-01 --to 2025-01-31
    - bench backup-doctype User --from 2025-01-01 --to 2025-01-31 --site mysite
    - bench backup-doctype User --from 2025-01-01
    - bench backup-doctype User --to 2025-01-31
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

    # Validate and parse date range if provided
    start_date_obj = None
    end_date_obj = None
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            click.echo(colored("Error: Invalid start date format. Use YYYY-MM-DD.", 'black', 'on_red'))
            frappe.destroy()
            return
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            click.echo(colored("Error: Invalid end date format. Use YYYY-MM-DD.", 'black', 'on_red'))
            frappe.destroy()
            return
    if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
        click.echo(colored("Error: Start date cannot be after end date.", 'black', 'on_red'))
        frappe.destroy()
        return

    # Create backup directory
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_dir = os.path.join('..', 'sites', 'backup', 'doctype', doctype)
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f"{doctype}-{timestamp}.json")

    # Fetch documents within the date range
    try:
        if start_date_obj and end_date_obj:
            query = f"""
                SELECT * FROM `tab{doctype}`
                WHERE creation BETWEEN '{start_date}' AND '{end_date}'
            """
        elif start_date_obj:
            query = f"""
                SELECT * FROM `tab{doctype}`
                WHERE creation >= '{start_date}'
            """
        elif end_date_obj:
            query = f"""
                SELECT * FROM `tab{doctype}`
                WHERE creation <= '{end_date}'
            """
        else:
            query = f"SELECT * FROM `tab{doctype}`"
        documents = frappe.db.sql(query, as_dict=True)

        # Fetch child table data
        child_tables = frappe.get_all("DocField", filters={"parent": doctype, "fieldtype": "Table"}, fields=["options"])
        for child_table in child_tables:
            for doc in documents:
                child_query = f"SELECT * FROM `tab{child_table.options}` WHERE parent = '{doc['name']}'"
                doc[child_table.options] = frappe.db.sql(child_query, as_dict=True)

        # Save documents to JSON file
        with open(backup_file, 'w') as f:
            json.dump(documents, f, indent=4, default=json_datetime_handler)

        click.echo(colored(f"Backup completed for Doctype '{doctype}'", 'black', 'on_green'))
    except Exception as e:
        click.echo(colored(f"Error backing up Doctype '{doctype}': {e}", 'black', 'on_red'))
    finally:
        frappe.destroy()

commands = [backup_doctype]