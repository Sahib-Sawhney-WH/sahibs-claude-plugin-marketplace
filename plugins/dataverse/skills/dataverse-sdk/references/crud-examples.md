# Dataverse CRUD Examples

## Create Operations

### Single Record Create
```python
# Create an account
account_data = {
    "name": "Contoso Ltd",
    "telephone1": "555-0100",
    "websiteurl": "https://contoso.com"
}
ids = client.create("account", account_data)
account_id = ids[0]
print(f"Created account: {account_id}")

# Create a contact
contact_data = {
    "firstname": "John",
    "lastname": "Doe",
    "emailaddress1": "john.doe@contoso.com"
}
contact_ids = client.create("contact", contact_data)
```

### Bulk Create
```python
# Create multiple records efficiently
records = [
    {"name": "Company A", "telephone1": "555-0001"},
    {"name": "Company B", "telephone1": "555-0002"},
    {"name": "Company C", "telephone1": "555-0003"},
]
ids = client.create("account", records)
print(f"Created {len(ids)} accounts")

# With custom table (note prefix)
custom_records = [
    {"new_name": "Item 1", "new_value": 100},
    {"new_name": "Item 2", "new_value": 200},
]
ids = client.create("new_customtable", custom_records)
```

### Create with Lookup Reference
```python
# Create contact linked to account
contact = {
    "firstname": "Jane",
    "lastname": "Smith",
    "parentcustomerid_account@odata.bind": f"/accounts({account_id})"
}
contact_ids = client.create("contact", contact)
```

### Create with Enum/Picklist
```python
from enum import IntEnum

class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

# Using enum value
record = {
    "new_name": "Task 1",
    "new_priority": Priority.HIGH  # Will be converted to 3
}

# Or using string label (SDK converts automatically)
record = {
    "new_name": "Task 2",
    "new_priority": "High"  # SDK converts to integer
}
```

## Read Operations

### Get Single Record
```python
# Get by ID
account = client.get("account", account_id)
print(f"Name: {account['name']}")

# Get specific columns only
account = client.get("account", account_id, select=["name", "telephone1"])
```

### Query Multiple Records
```python
# Basic query
pages = client.get("account")
for page in pages:
    for record in page:
        print(record["name"])

# With filter
pages = client.get(
    "account",
    filter="statecode eq 0 and name ne null"
)

# With select, filter, order
pages = client.get(
    "account",
    select=["name", "telephone1", "createdon"],
    filter="statecode eq 0",
    orderby=["createdon desc"],
    top=50
)
```

### Query with Expansion
```python
# Expand related records
pages = client.get(
    "account",
    select=["name"],
    expand=["primarycontactid"]
)
for page in pages:
    for account in page:
        contact = account.get("primarycontactid", {})
        print(f"{account['name']} - {contact.get('fullname', 'N/A')}")
```

### SQL Query
```python
# Read-only SQL queries
results = client.query_sql(
    "SELECT TOP 10 accountid, name, telephone1 "
    "FROM account "
    "WHERE statecode = 0 "
    "ORDER BY createdon DESC"
)
for row in results:
    print(f"{row['name']}: {row.get('telephone1', 'N/A')}")
```

## Update Operations

### Single Update
```python
# Update specific fields
client.update("account", account_id, {
    "telephone1": "555-0199",
    "description": "Updated via SDK"
})

# Verify update
updated = client.get("account", account_id, select=["telephone1"])
print(f"New phone: {updated['telephone1']}")
```

### Bulk Update
```python
# Update multiple records with same values
record_ids = ["id1", "id2", "id3"]
client.update("account", record_ids, {
    "new_status": "Processed",
    "new_processeddate": datetime.now().isoformat()
})

# Update each record differently
for record_id, value in zip(record_ids, [100, 200, 300]):
    client.update("account", record_id, {"new_amount": value})
```

### Clear Field Value
```python
# Set field to null
client.update("account", account_id, {
    "description": None
})
```

## Delete Operations

### Single Delete
```python
client.delete("account", account_id)
```

### Bulk Delete
```python
# Delete multiple records
record_ids = ["id1", "id2", "id3"]
job_id = client.delete("account", record_ids, use_bulk_delete=True)
print(f"Bulk delete job: {job_id}")
```

### Soft Delete (Deactivate)
```python
# Deactivate instead of delete
client.update("account", account_id, {
    "statecode": 1,  # Inactive
    "statuscode": 2  # Inactive status
})
```

## Working with Custom Tables

```python
# Custom table name includes prefix
TABLE = "new_myentity"

# Column names also include prefix
record = {
    "new_name": "My Record",
    "new_description": "Description text",
    "new_amount": 1500.50,
    "new_isactive": True,
    "new_quantity": 10
}

ids = client.create(TABLE, record)

# Query custom table
pages = client.get(
    TABLE,
    select=["new_name", "new_amount"],
    filter="new_isactive eq true"
)
```

## Handling Paging

```python
# Collect all records
all_records = []
pages = client.get("account", top=1000)
for page in pages:
    all_records.extend(page)
print(f"Total: {len(all_records)} records")

# Process in batches
pages = client.get("account", page_size=100)
batch_num = 0
for page in pages:
    batch_num += 1
    print(f"Processing batch {batch_num} with {len(page)} records")
    for record in page:
        # Process each record
        pass
```

## Transaction-like Pattern

```python
created_ids = []
try:
    # Create multiple related records
    account_ids = client.create("account", {"name": "New Account"})
    created_ids.append(("account", account_ids[0]))

    contact_ids = client.create("contact", {
        "firstname": "John",
        "parentcustomerid_account@odata.bind": f"/accounts({account_ids[0]})"
    })
    created_ids.append(("contact", contact_ids[0]))

except Exception as e:
    # Rollback on error
    print(f"Error: {e}. Rolling back...")
    for table, record_id in reversed(created_ids):
        try:
            client.delete(table, record_id)
        except:
            pass
    raise
```
