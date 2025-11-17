# 📖 GET Data API Documentation

A powerful, configuration-driven GET API system for retrieving data from Frappe DocTypes with advanced filtering, pagination, search, and relationship support.

---

## 🚀 Quick Start

### Basic Request
```bash
GET /api/method/core.factory.api.get_data?key=users&page=1&limit=20
```

### Response
```json
{
  "status": "success",
  "status_code": 200,
  "message": "Data loaded successfully",
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

---

## 📋 Table of Contents

1. [Configuration](#-configuration)
2. [Query Parameters](#-query-parameters)
3. [Advanced Features](#-advanced-features)
4. [Filters](#-filters)
5. [Child Tables & Relationships](#-child-tables--relationships)
6. [Error Handling](#-error-handling)
7. [Limitations](#-limitations)
8. [Examples](#-examples)

---

## ⚙️ Configuration

Create configurations in `yourapp/config/api_configs.py`:
```python
GET_CONFIGS = {
    "users": {
        "doctype": "User",
        "fields": ["name", "email", "first_name", "enabled"],
        "roles": ["System Manager"],
        
        # Optional: Custom messages
        "custom_messages": {
            "success_message": "Users retrieved successfully",
            "error_message": "Failed to fetch users"
        },
        
        # Optional: Sorting
        "order_by": "first_name asc",
        
        # Optional: Date filtering
        "date_field": "creation",
        
        # Optional: Search
        "search_fields": ["first_name", "email"],
        
        # Optional: Default pagination
        "limit": 20,
        
        # Optional: Static filters (always applied)
        "filters": {
            "static": {
                "enabled": 1
            },
            # Optional: User-provided filters
            "optional": ["department", "designation"]
        }
    }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `doctype` | string | Target DocType name |
| `fields` | array | Fields to retrieve |
| `roles` | array | Allowed user roles |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `order_by` | string | `"creation desc"` | Sorting order |
| `date_field` | string | `"creation"` | Field for date filtering |
| `search_fields` | array | `["name"]` | Fields for fuzzy search |
| `limit` | integer | `20` | Default records per page |
| `flat_payload` | boolean | `false` | Flatten child/related data |
| `custom_messages` | object | `{}` | Custom success/error messages |

---

## 🔍 Query Parameters

### Core Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `key` | string | ✅ | Configuration key | `?key=users` |
| `page` | integer | ❌ | Page number (1-based) | `?page=2` |
| `limit` | integer | ❌ | Records per page (max: 100) | `?limit=50` |
| `from_date` | datetime | ❌ | Start date filter | `?from_date=2024-01-01` |
| `to_date` | datetime | ❌ | End date filter | `?to_date=2024-12-31` |
| `query` | string | ❌ | Search query | `?query=john` |

### Example
```bash
GET /api/method/core.factory.api.get_data?key=users&page=2&limit=10&query=john&from_date=2024-01-01
```

---

## 🎯 Advanced Features

### 1. Multiple Search Terms

Search across multiple terms using comma separation:
```bash
GET /api/method/core.factory.api.get_data?key=users&query=john,jane,robert
```

**Result**: Matches records containing "john" OR "jane" OR "robert" in any search field.

---

### 2. OR Logic Filters

Use `or_static` filters for alternative filter groups:
```python
"filters": {
    "static": {
        "department": "Sales"  # Group A
    },
    "or_static": {
        "role": "Manager"      # Group B
    }
}
```

**SQL**: `(department = 'Sales') OR (role = 'Manager')`

---

### 3. System Fields

Access Frappe system fields:
```python
"fields": ["name", "_user_tags", "_comments", "_assign", "_liked_by"]
```

---

## 🔧 Filters

### Static Filters

Always applied, support dynamic resolution:
```python
"filters": {
    "static": {
        # Simple equality
        "enabled": 1,
        
        # Function resolution
        "department": "path.to.get_user_department",
        
        # Complex operators
        "status": {
            "IN": ["Active", "Pending"]
        },
        "salary": {
            ">=": 50000
        }
    }
}
```

### Optional Filters

User-provided via query parameters:
```python
"filters": {
    "optional": ["department", "designation", "status"]
}
```

**Usage**:
```bash
# Simple equality
GET /api/method/core.factory.api.get_data?key=users&department=Sales

# With operators
GET /api/method/core.factory.api.get_data?key=users&salary__gte=50000

# List operations
GET /api/method/core.factory.api.get_data?key=users&department__in=Sales,Marketing
```

### Supported Operators

| Operator | Suffix | Example | SQL |
|----------|--------|---------|-----|
| Equals | `__eq` or none | `status=Active` | `status = 'Active'` |
| Not Equals | `__ne` | `status__ne=Inactive` | `status != 'Inactive'` |
| Greater Than | `__gt` | `salary__gt=50000` | `salary > 50000` |
| Greater/Equal | `__gte` | `salary__gte=50000` | `salary >= 50000` |
| Less Than | `__lt` | `age__lt=30` | `age < 30` |
| Less/Equal | `__lte` | `age__lte=65` | `age <= 65` |
| In List | `__in` | `dept__in=Sales,HR` | `dept IN ('Sales','HR')` |
| Not In | `__nin` | `status__nin=Draft,Cancelled` | `status NOT IN (...)` |
| Like | `__like` | `email__like=@company.com` | `email LIKE '%@company.com%'` |
| Starts With | `__startswith` | `name__startswith=John` | `name LIKE 'John%'` |
| Ends With | `__endswith` | `email__endswith=.com` | `email LIKE '%.com'` |
| Contains | `__contains` | `desc__contains=urgent` | `desc LIKE '%urgent%'` |
| Is Null | `__isnull` | `phone__isnull=true` | `phone IS NULL` |
| Not Null | `__notnull` | `email__notnull=true` | `email IS NOT NULL` |
| Is Empty | `__isempty` | `notes__isempty=true` | `notes IS NULL OR notes = ''` |
| Not Empty | `__notempty` | `name__notempty=true` | `name IS NOT NULL AND name != ''` |
| Between | `__between` | `salary__between=30000,50000` | `salary BETWEEN 30000 AND 50000` |
| Date Equals | `__date` | `created__date=2024-01-01` | `DATE(created) = '2024-01-01'` |
| Year Equals | `__year` | `created__year=2024` | `YEAR(created) = 2024` |
| Month Equals | `__month` | `created__month=12` | `MONTH(created) = 12` |
| Day Equals | `__day` | `created__day=15` | `DAY(created) = 15` |

---

## 👨‍👩‍👧 Child Tables & Relationships

### Child Table Configuration
```python
"child_table": {
    "doctype": "Sales Order Item",
    "parent_field": "items",           # Field name in parent
    "fields": ["item_code", "qty", "rate"],
    
    # Optional: Custom result field name
    "result_field_name": "line_items",
    
    # Optional: Sorting
    "order_by": "idx asc",
    
    # Optional: Filters
    "filters": {
        "static": {
            "delivered": 0
        }
    }
}
```

### Related Parent Data
```python
"related_parents": [
    {
        "doctype": "Customer",
        "link_field": "customer",      # Field in main doctype
        "rel_field": "name",           # Field in related doctype
        "fields": ["customer_name", "territory"],
        "is_single": True,             # Return single object vs array
        "result_field_name": "customer_details"
    }
]
```

### Flat vs Structured Payload

**Structured (default)**:
```json
{
  "name": "ORD-001",
  "customer": "CUST-001",
  "items": [
    {"item_code": "ITEM-1", "qty": 10},
    {"item_code": "ITEM-2", "qty": 5}
  ],
  "customer_details": {
    "customer_name": "Acme Corp",
    "territory": "North"
  }
}
```

**Flat** (`flat_payload: true`):
```json
{
  "name": "ORD-001",
  "customer": "CUST-001",
  "item_code": "ITEM-1",
  "qty": 10,
  "customer_name": "Acme Corp",
  "territory": "North"
}
```

⚠️ **Note**: Flat mode only returns the first child/related record.

---

## ⚠️ Error Handling

### Error Response Format
```json
{
  "status": "error",
  "status_code": 400,
  "message": "Validation failed: Invalid field 'invalid_field'"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `200` | Success | Request completed successfully |
| `400` | Bad Request | Invalid key, malformed parameters |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Configuration not found |
| `422` | Validation Error | Invalid filters, field names |
| `500` | Server Error | Internal processing error |

### Common Errors

**Invalid Configuration Key**:
```json
{
  "status": "error",
  "status_code": 400,
  "message": "Invalid or missing configuration key"
}
```

**Permission Denied**:
```json
{
  "status": "error",
  "status_code": 403,
  "message": "Access denied. You don't have the required permissions."
}
```

**Invalid Field**:
```json
{
  "status": "error",
  "status_code": 422,
  "message": "Validation failed: Invalid fields for User: invalid_field"
}
```

---

## 🚫 Limitations

### Hard Limits

| Limit | Value | Description |
|-------|-------|-------------|
| Max records per page | `100` | Cannot exceed via `limit` parameter |
| Max search fields | `50` | Maximum fields in `search_fields` |
| Max filter depth | `3` levels | For nested filter operations |
| Max OR filter groups | `2` | `static` + `or_static` only |
| Query parameter length | `8192` chars | URL length limit |

### Performance Considerations

1. **Large Datasets**: Pagination required for >10,000 records
2. **Complex Queries**: Combine <5 filters for optimal performance
3. **Child Tables**: Limit to 2-3 levels of nesting
4. **Search**: Avoid wildcard searches on large text fields

### Security Restrictions

1. **Permission Checks**: 
   - User must have at least one role from `roles` array
   - Optional: Department-based access via `dept` array

2. **Field Access**:
   - Only configured fields are accessible
   - System fields require explicit inclusion

3. **SQL Injection Prevention**:
   - All inputs sanitized and parameterized
   - Field names validated against DocType meta

### Behavioral Notes

1. **Empty Values**: 
   - Null/empty optional filters are automatically skipped
   - Use `__isnull` operator for explicit null checks

2. **Date Filtering**:
   - Uses configured `date_field` (default: `creation`)
   - Inclusive range: `from_date <= date <= to_date`

3. **Search Logic**:
   - OR logic across all search fields
   - Partial matching with wildcards
   - Case-insensitive by default

4. **Flat Payload Mode**:
   - Only first child/related record returned
   - Field name conflicts resolved by last-write-wins

---

## 📚 Examples

### Example 1: Basic User Listing

**Configuration**:
```python
GET_CONFIGS = {
    "active_users": {
        "doctype": "User",
        "fields": ["name", "email", "first_name"],
        "roles": ["System Manager"],
        "filters": {
            "static": {
                "enabled": 1
            }
        }
    }
}
```

**Request**:
```bash
GET /api/method/core.factory.api.get_data?key=active_users&page=1&limit=10
```

---

### Example 2: Advanced Filtering

**Request**:
```bash
GET /api/method/core.factory.api.get_data?key=employees&department__in=Sales,Marketing&salary__gte=50000&status__ne=Inactive
```

**SQL Generated**:
```sql
WHERE department IN ('Sales', 'Marketing') 
  AND salary >= 50000 
  AND status != 'Inactive'
```

---

### Example 3: Sales Orders with Items

**Configuration**:
```python
GET_CONFIGS = {
    "orders_with_items": {
        "doctype": "Sales Order",
        "fields": ["name", "customer", "grand_total", "status"],
        "roles": ["Sales User"],
        "child_table": {
            "doctype": "Sales Order Item",
            "parent_field": "items",
            "fields": ["item_code", "qty", "rate", "amount"]
        },
        "flat_payload": False
    }
}
```

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "name": "SAL-ORD-2024-00001",
      "customer": "Acme Corp",
      "grand_total": 15000,
      "status": "Submitted",
      "items": [
        {
          "item_code": "ITEM-001",
          "qty": 10,
          "rate": 1000,
          "amount": 10000
        },
        {
          "item_code": "ITEM-002",
          "qty": 5,
          "rate": 1000,
          "amount": 5000
        }
      ]
    }
  ],
  "pagination": {...}
}
```

---

### Example 4: Date Range with Search

**Request**:
```bash
GET /api/method/core.factory.api.get_data?key=orders&from_date=2024-01-01&to_date=2024-12-31&query=acme,global
```

**Filters Applied**:
1. Date range: `creation >= '2024-01-01' AND creation <= '2024-12-31'`
2. Search: `(customer LIKE '%acme%' OR customer LIKE '%global%' OR name LIKE '%acme%' OR name LIKE '%global%')`

---

### Example 5: OR Logic Filters

**Configuration**:
```python
"filters": {
    "static": {
        "department": "Sales"
    },
    "or_static": {
        "designation": "Manager"
    }
}
```

**SQL**: `WHERE (department = 'Sales') OR (designation = 'Manager')`

---

### Example 6: Related Customer Data

**Configuration**:
```python
GET_CONFIGS = {
    "orders_with_customer": {
        "doctype": "Sales Order",
        "fields": ["name", "customer", "grand_total"],
        "roles": ["Sales User"],
        "related_parents": [
            {
                "doctype": "Customer",
                "link_field": "customer",
                "rel_field": "name",
                "fields": ["customer_name", "territory", "customer_group"],
                "is_single": True,
                "result_field_name": "customer_info"
            }
        ]
    }
}
```

**Response**:
```json
{
  "name": "SAL-ORD-2024-00001",
  "customer": "CUST-00001",
  "grand_total": 15000,
  "customer_info": {
    "customer_name": "Acme Corporation",
    "territory": "North America",
    "customer_group": "Commercial"
  }
}
```

---

## 🔐 Security Best Practices

1. **Always Configure Roles**: Never use empty `roles` array
2. **Limit Field Exposure**: Only expose necessary fields
3. **Use Static Filters**: Enforce data access boundaries
4. **Validate Optional Filters**: Only allow safe filter fields
5. **Monitor API Usage**: Track requests via logs

---

## 📊 Monitoring & Debugging

### Get Configuration Info
```bash
GET /api/method/core.factory.api.get_config_info?key=users
```

### List All Configurations
```bash
GET /api/method/core.factory.api.get_config_info
```

### Test API Status
```bash
GET /api/method/core.factory.api.test_get_api
```

---

## 🛠️ Troubleshooting

### Issue: Permission Denied

**Cause**: User lacks required roles  
**Solution**: Add user to one of the configured roles

### Issue: No Data Returned

**Cause**: Static filters exclude all records  
**Solution**: Review static filter values

### Issue: Invalid Field Error

**Cause**: Field doesn't exist in DocType  
**Solution**: Verify field names in DocType meta

### Issue: Slow Performance

**Causes**:
- Too many search fields
- Complex nested relationships
- Large result sets without pagination

**Solutions**:
- Reduce search fields
- Use flat_payload for simple queries
- Implement proper pagination

---

## 📝 Changelog

### v1.0.0
- Initial release
- Configuration-driven GET API
- Support for filters, search, pagination
- Child tables and related data
- Custom messages
- Operation-specific logging

---

## 🤝 Contributing

Report issues and suggestions at: [GitHub Issues](https://github.com/yourrepo/issues)

---

## 📄 License

[Your License Here]

---

## 🆘 Support

- **Documentation**: [Link to full docs]
- **Community**: [Link to community forum]
- **Email**: support@yourcompany.com

---

**Last Updated**: 2024
**API Version**: 1.0.0
