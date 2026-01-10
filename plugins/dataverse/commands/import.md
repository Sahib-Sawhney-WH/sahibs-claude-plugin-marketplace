---
description: Import data from CSV or JSON file into Dataverse
argument-hint: "<table_name> <file_path>"
allowed-tools:
  - Read
  - Bash
  - mcp__dataverse__dataverse_connect
  - mcp__dataverse__dataverse_create_records
  - mcp__dataverse__dataverse_get_table_info
  - AskUserQuestion
---

# Dataverse Import Command

Import data from a CSV or JSON file into a Dataverse table.

## Instructions

When the user runs `/dataverse:import <table> <file>`:

1. **Parse arguments**
   - Table name (schema name like "account" or "new_mytable")
   - File path (CSV or JSON)

2. **Validate inputs**
   - Check file exists
   - Determine file type from extension
   - Get table schema to validate columns

3. **Read and parse file**
   - For CSV: Parse with headers as column names
   - For JSON: Expect array of objects

4. **Map columns**
   - Show detected columns
   - Ask user to confirm mapping to Dataverse columns
   - Handle column name case differences

5. **Import data**
   - Use `dataverse_create_records` for bulk import
   - Process in batches of 100 records
   - Report progress

6. **Report results**
   - Records imported successfully
   - Any errors encountered
   - Record IDs created

### CSV Format Example
```csv
name,telephone1,websiteurl
Contoso,555-0100,https://contoso.com
Fabrikam,555-0200,https://fabrikam.com
```

### JSON Format Example
```json
[
  {"name": "Contoso", "telephone1": "555-0100"},
  {"name": "Fabrikam", "telephone1": "555-0200"}
]
```

### Column Mapping

If CSV/JSON column names don't match Dataverse exactly:
- Show the mapping
- Allow user to confirm or adjust
- Lowercase column names automatically

### Error Handling

- Validate required columns exist
- Check data types match
- Report failed records with reason
- Continue processing on individual record errors
