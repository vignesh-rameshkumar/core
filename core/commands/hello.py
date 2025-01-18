from __future__ import unicode_literals, absolute_import
import click

@click.command('hello_world')
def hello_world():
    """This is a custom bench command."""
    click.echo("Hello from custom bench command!")

commands = [hello_world]