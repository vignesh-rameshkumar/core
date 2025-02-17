from .hello import hello_world
from .backup_app import backup_app
from .restore_app import restore_app
from .delete_app import delete_app
from .backup_doctype import backup_doctype

from .restore_doctype import restore_doctype

commands = [
    hello_world,
    backup_app,
    restore_app,
    delete_app,
    backup_doctype,
    restore_doctype,
]