from . import __version__ as app_version

app_name = "core"
app_title = "Agnikul Core ERP"
app_publisher = "Agnikul Cosmos Private Limited"
app_description = "Core ERP System for Agnikul Cosmos"
app_email = "automationbot@agnikul.in"
app_license = "MIT"


doc_events = {
    "AGK_Projects": {
        "before_save": "core.api.role.pl"
    }
}

fixtures = [
    {
        "dt": "Custom DocPerm",
        "filters": [["parent", "in", ["AGK_MIS", "AGK_Projects","AGK_Departments","AGK_Facilities","AGK_Rigs"]]]
    }
]
