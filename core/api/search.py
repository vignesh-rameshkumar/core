import frappe
from frappe.utils import cstr

@frappe.whitelist(allow_guest=True)
def search(query):
    """
    Global search API that returns results based on the provided query.
    """
    query = f"%{query}%"
    results = {
        "projects": set(),
        "departments": set(),
        "facilities": set(),
        "rigs": set(),
        "mis": set()
    }

    # Search Rigs
    rigs = frappe.db.sql("""
        SELECT rig_name as name, rig_code as code
        FROM `tabAGK_Rigs`
        WHERE status = 'Active'
        AND (rig_name LIKE %(query)s OR rig_code LIKE %(query)s)
    """, {'query': query}, as_dict=1)
    for rig in rigs:
        results["rigs"].add((rig.name, rig.code))

    # Search Facilities
    facilities = frappe.db.sql("""
        SELECT facility_name as name, facility_code as code
        FROM `tabAGK_Facilities`
        WHERE status = 'Active'
        AND (facility_name LIKE %(query)s OR facility_code LIKE %(query)s)
    """, {'query': query}, as_dict=1)
    for facility in facilities:
        results["facilities"].add((facility.name, facility.code))

    # Search MIS and MIS Subcategories
    mis = frappe.db.sql("""
        SELECT category as name, mis_indicator
        FROM `tabAGK_MIS`
        WHERE category LIKE %(query)s OR mis_indicator LIKE %(query)s
    """, {'query': query}, as_dict=1)
    for m in mis:
        results["mis"].add((m.name, m.mis_indicator))

    mis_subcategories = frappe.db.sql("""
        SELECT category as name, code
        FROM `tabMIS Subcategories`
        WHERE category LIKE %(query)s OR code LIKE %(query)s
    """, {'query': query}, as_dict=1)
    for sub in mis_subcategories:
        results["mis"].add((sub.name, sub.code))

    # Search Projects and Project Details
    projects = frappe.db.sql("""
        SELECT pd.name1 as name, pd.code as detail_code
        FROM `tabAGK_Projects` p
        LEFT JOIN `tabProject Detail` pd ON pd.parent = p.name
        WHERE p.status = 'Active'
        AND (
            p.project_name LIKE %(query)s
            OR p.indicator LIKE %(query)s
            OR pd.name1 LIKE %(query)s
            OR pd.code LIKE %(query)s
        )
    """, {'query': query}, as_dict=1)
    for project in projects:
        results["projects"].add((project.name, project.detail_code))

    # Search Departments
    departments = frappe.db.sql("""
        SELECT department_name as name, department_code as code
        FROM `tabAGK_Departments`
        WHERE department_name LIKE %(query)s OR department_code LIKE %(query)s
    """, {'query': query}, as_dict=1)
    for department in departments:
        results["departments"].add((department.name, department.code))

    # Convert sets to lists of dictionaries
    return {
        category: [
            {"name": name, "code": code}
            for name, code in items
        ]
        for category, items in results.items()
    }
