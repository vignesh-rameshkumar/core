from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "core"
app_title = "Agnikul Core ERP"
app_publisher = "Agnikul Cosmos Private Limited"
app_description = "Core ERP System for Agnikul Cosmos"
app_email = "automationbot@agnikul.in"
app_license = "MIT"

after_install = "core.api.install.create_roles"
after_migrate = "core.sync_handler.clear_sync_cache"


doc_events = {
    "AGK_Projects": {
        "before_save": "core.api.pl_role.assign"
    },
    "AGK_Departments": {
        "before_save": "core.api.dl_role.assign"
    },
    "AGK_ERP_Products": {
        "before_insert": "core.api.products.create",
        "before_save": "core.api.products.assign"
    },
    "AGK_Facilities": {
        "before_insert": "core.api.facility.security",
        "validate": "core.api.facility.validate_status"
    },

    "Desk Settings":{
        "on_update": "core.update_desk_cache"
    },
    "Employee": {
        "before_validate": "core.api.employee.before_validate",
        "validate": "core.api.employee.validate_user_status",
        "before_save": "core.api.employee.before_save"
    },
    "*": {
        "after_insert": "core.sync_handler.process_doc_event",
        "on_update": "core.sync_handler.process_doc_event",
        "on_submit": "core.sync_handler.process_doc_event",
        "before_cancel": "core.sync_handler.process_doc_event",
        "on_trash": "core.sync_handler.process_doc_event"
    }
}

website_route_rules = [{'from_route': '/erp-desk/<path:app_path>', 'to_route': 'erp-desk'},]