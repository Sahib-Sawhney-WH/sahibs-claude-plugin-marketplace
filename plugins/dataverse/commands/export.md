---
description: Export Dataverse table data to CSV or JSON file
argument-hint: "<table_name> [output_file]"
allowed-tools:
  - Write
  - mcp__dataverse__dataverse_connect
  - mcp__dataverse__dataverse_query
  - mcp__dataverse__dataverse_get_table_info
  - AskUserQuestion
---

# Dataverse Export Command

Export data from a Dataverse table to a CSV or JSON file.

## Instructions

When the user runs `/dataverse:export <table> [file]`:

1. **Parse arguments**
   - Table name (required)
   - Output file path (optional, default: `<table>_export.csv`)

2. **Get table schema**
   - Use `dataverse_get_table_info` to get columns
   - Show available columns to user

3. **Configure export**
   - Ask which columns to export (or all)
   - Ask for any filter criteria
   - Ask for max records (default: 1000)

4. **Query data**
   - Use `dataverse_query` with select and filter
   - Handle paging for large datasets

5. **Write output file**
   - CSV: Write with headers
   - JSON: Write as array of objects
   - Determine format from file extension

6. **Report results**
   - Records exported
   - Output file path
   - File size

### Export Options

Ask user about:
- Columns to include
- Filter expression (e.g., "statecode eq 0")
- Sort order
- Maximum records

### Output Formats

**CSV (default):**
```csv
accountid,name,telephone1
00000000-0000-0000-0000-000000000001,Contoso,555-0100
00000000-0000-0000-0000-000000000002,Fabrikam,555-0200
```

**JSON:**
```json
[
  {"accountid": "00000000-...", "name": "Contoso", "telephone1": "555-0100"},
  {"accountid": "00000000-...", "name": "Fabrikam", "telephone1": "555-0200"}
]
```

### Best Practices

- Always include the primary key column
- Use filters to limit data exported
- Be cautious with large tables
- Consider security/privacy of exported data
