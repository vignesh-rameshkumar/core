# API Documentation

This document provides an overview of the available APIs, their endpoints, supported parameters, and sample responses.

---

## Departments API

### Endpoint
`/api/method/core.api.departments.list`

### Parameters
None

### Sample Response
```json
[
    {
        "department_name": "Human Resource",
        "department_code": "D0001",
        "primary_approver": "adithi@agnikul.in"
    },
    {
        "department_name": "IT",
        "department_code": "D0002",
        "primary_approver": "arjunan@agnikul.in"
    }
]
```

---

### Endpoint
`/api/method/core.api.departments.approvers`

### Parameters
- `department_name` (string): The name of the department.

### Sample Response
```json
{
    "primary_approver": "arjunan@agnikul.in",
    "proxy_approver": "adithi@agnikul.in"
}
```

---

## Facility API

### Endpoint
`/api/method/core.api.facility.list`

### Parameters
None

### Sample Response
```json
[
    {
        "facility_name": "Thaiyur",
        "facility_code": "F0001"
    },
    {
        "facility_name": "Research Park",
        "facility_code": "F0002"
    }
]
```

---

## MIS API

### Endpoint
`/api/method/core.api.mis.list`

### Parameters
- `is_product` (boolean, optional): Filter by is_product status (`1` or `0`).

### Sample Response
```json
[
    {
        "name": "MIS001",
        "category": "Category A",
        "is_product": true,
        "mis_indicator": "Indicator A",
        "sub_categories": [
            {
                "category": "Subcategory A1",
                "code": "Code A1"
            },
            {
                "category": "Subcategory A2",
                "code": "Code A2"
            }
        ]
    }
]
```

---

## Projects API

### Endpoint
`/api/method/core.api.projects.list`

### Parameters
- `limit` (integer, optional): Number of records to fetch. Default is 20.
- `start` (integer, optional): Starting index for pagination. Default is 0.

### Sample Response
```json
{
    "details": [
        {
            "name1": "Project A",
            "code": "P0001",
            "approver": "adithi@agnikul.in"
        },
        {
            "name1": "Project B",
            "code": "P0002",
            "approver": "arjunan@agnikul.in"
        }
    ],
    "has_more": true,
    "next_start": 20
}
```

### Endpoint
`/api/method/core.api.projects.approvers`

### Parameters
- `code` (string): The code of the Project.

### Sample Response
```json
{
    "primary_approver": "arjunan@agnikul.in",
    "proxy_approver": "adithi@agnikul.in"
}
```

---

## Rigs API

### Endpoint
`/api/method/core.api.rigs.list`

### Parameters
None

### Sample Response
```json
[
    {
        "rig_name": "Rig A",
        "rig_code": "R001"
    },
    {
        "rig_name": "Rig B",
        "rig_code": "R002"
    }
]
```

---

This documentation provides a comprehensive overview of the available APIs and their usage.