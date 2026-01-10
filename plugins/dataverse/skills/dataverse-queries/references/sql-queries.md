# Dataverse SQL Query Reference

## Overview

Dataverse supports read-only SQL queries via the Web API `?sql=` parameter. The SDK provides `query_sql()` method for this.

## Basic Syntax

```python
results = client.query_sql("SELECT column1, column2 FROM tablename WHERE condition")
```

## SELECT Statement

```sql
-- Select specific columns
SELECT name, telephone1 FROM account

-- Select all columns
SELECT * FROM account

-- With alias
SELECT name AS AccountName, telephone1 AS Phone FROM account
```

## WHERE Clause

```sql
-- Equality
SELECT * FROM account WHERE statecode = 0

-- Comparison
SELECT * FROM account WHERE revenue > 1000000

-- Multiple conditions
SELECT * FROM account WHERE statecode = 0 AND revenue > 1000000

-- String comparison
SELECT * FROM account WHERE name = 'Contoso'

-- LIKE pattern
SELECT * FROM account WHERE name LIKE 'Con%'
SELECT * FROM account WHERE name LIKE '%toso'
SELECT * FROM account WHERE name LIKE '%tos%'

-- IN clause
SELECT * FROM account WHERE industrycode IN (1, 2, 3)

-- NULL check
SELECT * FROM account WHERE telephone1 IS NULL
SELECT * FROM account WHERE telephone1 IS NOT NULL

-- BETWEEN
SELECT * FROM account WHERE createdon BETWEEN '2024-01-01' AND '2024-12-31'
```

## ORDER BY

```sql
-- Ascending (default)
SELECT * FROM account ORDER BY name

-- Descending
SELECT * FROM account ORDER BY createdon DESC

-- Multiple columns
SELECT * FROM account ORDER BY statecode, name ASC, createdon DESC
```

## TOP / LIMIT

```sql
-- Limit results
SELECT TOP 10 * FROM account

-- With ORDER BY
SELECT TOP 100 name, revenue FROM account ORDER BY revenue DESC
```

## Aggregate Functions

```sql
-- COUNT
SELECT COUNT(*) FROM account WHERE statecode = 0

-- SUM
SELECT SUM(revenue) FROM account

-- AVG
SELECT AVG(numberofemployees) FROM account

-- MIN/MAX
SELECT MIN(createdon), MAX(createdon) FROM account

-- Combined
SELECT
    COUNT(*) AS total_count,
    SUM(revenue) AS total_revenue,
    AVG(revenue) AS avg_revenue
FROM account
WHERE statecode = 0
```

## GROUP BY

```sql
-- Group and count
SELECT industrycode, COUNT(*) AS count
FROM account
GROUP BY industrycode

-- Group with aggregate
SELECT
    industrycode,
    COUNT(*) AS count,
    SUM(revenue) AS total_revenue
FROM account
GROUP BY industrycode

-- HAVING clause
SELECT industrycode, COUNT(*) AS count
FROM account
GROUP BY industrycode
HAVING COUNT(*) > 10
```

## DISTINCT

```sql
-- Unique values
SELECT DISTINCT industrycode FROM account

-- Count distinct
SELECT COUNT(DISTINCT ownerid) FROM account
```

## Date Functions

```sql
-- Extract year
SELECT * FROM account WHERE YEAR(createdon) = 2024

-- Extract month
SELECT * FROM account WHERE MONTH(createdon) = 1

-- Date comparison
SELECT * FROM account WHERE createdon >= '2024-01-01'
```

## Limitations

### Not Supported
- **INSERT, UPDATE, DELETE** - Read-only queries only
- **JOINs** - No table joins (use OData $expand)
- **Subqueries** - No nested SELECT statements
- **UNION** - No combining queries
- **CTEs** - No WITH clauses
- **Window functions** - No OVER/PARTITION BY
- **Stored procedures** - No EXEC

### Limited Support
- **Functions** - Only basic aggregates and date functions
- **Data types** - Some column types may not work
- **Complex expressions** - Keep calculations simple

## Python Integration

```python
# Basic query
results = client.query_sql(
    "SELECT TOP 10 name, telephone1 FROM account WHERE statecode = 0"
)
for row in results:
    print(f"{row['name']}: {row.get('telephone1', 'N/A')}")

# Parameterized (string formatting - be careful with injection)
table_name = "account"
status = 0
results = client.query_sql(
    f"SELECT name FROM {table_name} WHERE statecode = {status}"
)

# Building complex queries
columns = ["name", "telephone1", "revenue"]
filters = ["statecode = 0", "revenue > 0"]
order = "revenue DESC"
limit = 50

query = f"""
SELECT TOP {limit} {', '.join(columns)}
FROM account
WHERE {' AND '.join(filters)}
ORDER BY {order}
"""
results = client.query_sql(query)
```

## Best Practices

1. **Always use TOP** - Limit results to avoid timeouts
2. **Select specific columns** - Don't use SELECT *
3. **Use indexed columns in WHERE** - statecode, ownerid, createdon
4. **Avoid LIKE with leading wildcard** - '%value' is slow
5. **Test queries** - Some syntax may not be supported
6. **Handle empty results** - Check for empty list return
