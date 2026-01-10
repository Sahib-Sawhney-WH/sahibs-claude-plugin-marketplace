# OData Query Syntax Reference

## Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `$select` | Columns to return | `$select=name,telephone1` |
| `$filter` | Filter expression | `$filter=statecode eq 0` |
| `$orderby` | Sort order | `$orderby=name asc` |
| `$top` | Max records | `$top=100` |
| `$expand` | Related entities | `$expand=primarycontactid` |
| `$count` | Include count | `$count=true` |

## Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `statecode eq 0` |
| `ne` | Not equal | `name ne null` |
| `gt` | Greater than | `revenue gt 1000000` |
| `ge` | Greater or equal | `createdon ge 2024-01-01` |
| `lt` | Less than | `quantity lt 10` |
| `le` | Less or equal | `amount le 500` |

## Logical Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `and` | Logical AND | `a eq 1 and b eq 2` |
| `or` | Logical OR | `a eq 1 or a eq 2` |
| `not` | Logical NOT | `not contains(name,'test')` |

## String Functions

| Function | Description | Example |
|----------|-------------|---------|
| `contains(field, value)` | Contains substring | `contains(name,'Contoso')` |
| `startswith(field, value)` | Starts with | `startswith(name,'A')` |
| `endswith(field, value)` | Ends with | `endswith(email,'@contoso.com')` |

## Date Functions

```
# Date comparisons use ISO 8601 format
createdon ge 2024-01-01
createdon ge 2024-01-01T00:00:00Z

# Date functions (limited support)
year(createdon) eq 2024
month(createdon) eq 1
day(createdon) eq 15
```

## Arithmetic Operators

| Operator | Example |
|----------|---------|
| `add` | `price add tax gt 100` |
| `sub` | `quantity sub sold gt 0` |
| `mul` | `price mul quantity gt 1000` |
| `div` | `total div count gt 50` |
| `mod` | `quantity mod 10 eq 0` |

## Null Handling

```
# Is null
field eq null

# Is not null
field ne null

# Coalesce (not directly supported - use logic)
(field ne null and field eq 'value') or field eq null
```

## GUID Values

```
# Filter by GUID
accountid eq 00000000-0000-0000-0000-000000000000

# Filter by lookup
_parentaccountid_value eq 00000000-0000-0000-0000-000000000000
```

## Collection Queries

```
# Related records (1:N)
$expand=contact_customer_accounts($select=fullname;$top=5)

# Filter expanded records
$expand=contact_customer_accounts($filter=statecode eq 0)
```

## Special Characters

Escape special characters in string values:
- Single quote: `''` (two single quotes)
- Percent: `%25`
- Ampersand: `%26`

```
# Name contains apostrophe
contains(name,'O''Brien')
```

## Case Sensitivity

- **Column names**: Case-insensitive in SDK (auto-lowercased)
- **Filter values**: Case-sensitive by default
- **Table names**: Use logical names (lowercase)

## Performance Tips

1. **Always use $select** - Limit returned columns
2. **Use $top** - Don't retrieve all records
3. **Filter on indexed columns** - statecode, ownerid, createdon
4. **Avoid contains()** - Use startswith() when possible
5. **Paginate large results** - Use page_size parameter
