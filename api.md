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
        "department_code": "D0001"
    },
    {
        "department_name": "IT",
        "department_code": "D0002"
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
    "primary_approver": "John Doe",
    "proxy_approver": "Jane Smith"
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
        "name": "Facility A",
        "location": "New York"
    },
    {
        "name": "Facility B",
        "location": "San Francisco"
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
            "code": "P0001"
        },
        {
            "name1": "Project B",
            "code": "P0002"
        }
    ],
    "has_more": true,
    "next_start": 20
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
