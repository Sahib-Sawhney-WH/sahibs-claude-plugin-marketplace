# dataverse-queries

This skill provides guidance on querying data from Microsoft Dataverse. Use when users ask about "Dataverse query", "OData filter", "Dataverse SQL", "FetchXML", "query Dataverse records", "Dataverse filter syntax", "search Dataverse", or need help constructing queries.

## Query Methods

The Dataverse SDK supports two query methods:
1. **OData queries** - Standard Web API query syntax
2. **SQL queries** - T-SQL-like syntax (read-only)

## OData Query Basics

```python
# Basic query - returns all records (paged)
pages = client.get("account")

# With parameters
pages = client.get(
    "account",
    select=["name", "telephone1"],      # Columns to return
    filter="statecode eq 0",            # Filter expression
    orderby=["name asc"],               # Sort order
    top=100,                            # Max records
    expand=["primarycontactid"]         # Related records
)

# Process results
for page in pages:
    for record in page:
        print(record["name"])
```

## OData Filter Syntax

### Comparison Operators
| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `statecode eq 0` |
| `ne` | Not equal | `name ne null` |
| `gt` | Greater than | `revenue gt 1000000` |
| `ge` | Greater or equal | `createdon ge 2024-01-01` |
| `lt` | Less than | `quantity lt 10` |
| `le` | Less or equal | `amount le 500` |

### Logical Operators
```python
# AND
filter="statecode eq 0 and revenue gt 1000000"

# OR
filter="name eq 'Contoso' or name eq 'Fabrikam'"

# NOT
filter="not contains(name, 'test')"

# Combined
filter="(statecode eq 0) and (revenue gt 1000000 or numberofemployees gt 100)"
```

### String Functions
```python
# Contains
filter="contains(name, 'Contoso')"

# Starts with
filter="startswith(name, 'A')"

# Ends with
filter="endswith(emailaddress1, '@contoso.com')"
```

### Date Filters
```python
# Specific date
filter="createdon ge 2024-01-01"

# Date range
filter="createdon ge 2024-01-01 and createdon lt 2024-02-01"

# Today (use ISO format)
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
filter=f"createdon ge {today}"
```

### Null Checks
```python
# Is null
filter="telephone1 eq null"

# Is not null
filter="telephone1 ne null"
```

## SQL Query Syntax

SQL queries are read-only and support a subset of T-SQL.

```python
# Basic SELECT
results = client.query_sql(
    "SELECT name, telephone1 FROM account WHERE statecode = 0"
)

# With TOP
results = client.query_sql(
    "SELECT TOP 10 name FROM account ORDER BY createdon DESC"
)

# With aggregates
results = client.query_sql(
    "SELECT industrycode, COUNT(*) as count "
    "FROM account "
    "GROUP BY industrycode"
)
```

### SQL Limitations
- **Read-only** - No INSERT, UPDATE, DELETE
- **Limited functions** - Basic aggregates only
- **No JOINs** - Use OData expand instead
- **No subqueries** - Keep queries simple

## Paging and Large Result Sets

```python
# Automatic paging (iterator)
all_records = []
pages = client.get("account", top=5000)
for page in pages:
    all_records.extend(page)

# Control page size
pages = client.get("account", page_size=500)

# Break early
pages = client.get("account", top=1000)
count = 0
for page in pages:
    for record in page:
        count += 1
        if count >= 100:
            break
    if count >= 100:
        break
```

## Select Specific Columns

Always specify columns to reduce payload:

```python
# Good - only needed columns
pages = client.get(
    "account",
    select=["accountid", "name", "telephone1"]
)

# Bad - returns all columns (slower)
pages = client.get("account")
```

## Expand Related Records

```python
# Expand single relationship
pages = client.get(
    "account",
    select=["name"],
    expand=["primarycontactid"]
)

# Access expanded data
for page in pages:
    for account in page:
        contact = account.get("primarycontactid", {})
        print(f"{account['name']}: {contact.get('fullname')}")
```

## Order By

```python
# Single column ascending
orderby=["name"]

# Single column descending
orderby=["createdon desc"]

# Multiple columns
orderby=["statecode", "name asc", "createdon desc"]
```

## Common Query Patterns

### Active Records Only
```python
pages = client.get("account", filter="statecode eq 0")
```

### Records Created Recently
```python
pages = client.get(
    "account",
    filter="createdon ge 2024-01-01",
    orderby=["createdon desc"]
)
```

### Search by Name
```python
pages = client.get(
    "account",
    filter="contains(name, 'Contoso')"
)
```

### Records with Specific Owner
```python
pages = client.get(
    "account",
    filter=f"_ownerid_value eq {user_id}"
)
```

### Count Records
```python
pages = client.get("account", filter="statecode eq 0")
count = sum(len(page) for page in pages)
```

## References

- See `references/odata-syntax.md` for complete OData reference
- See `references/sql-queries.md` for SQL query examples
