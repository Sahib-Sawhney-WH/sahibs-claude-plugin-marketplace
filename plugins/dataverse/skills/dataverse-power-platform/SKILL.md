# dataverse-power-platform

This skill provides guidance on integrating with the Microsoft Power Platform ecosystem. Use when users ask about "Power Apps", "Power Automate", "Power BI", "Dataverse connector", "canvas app", "model-driven app", "Power Automate flow", or need help with Power Platform integration.

## Power Apps Integration

### Canvas Apps with Dataverse
Canvas apps can connect to Dataverse tables as data sources.

**Connection setup:**
1. Add Dataverse connector in Power Apps
2. Select tables to use
3. Use formulas to read/write data

**Common formulas:**
```
// Read all accounts
ClearCollect(colAccounts, Accounts)

// Filter records
Filter(Accounts, Status = "Active")

// Create record
Patch(Accounts, Defaults(Accounts), {Name: "New Account"})

// Update record
Patch(Accounts, LookUp(Accounts, AccountId = varId), {Name: "Updated"})

// Delete record
Remove(Accounts, LookUp(Accounts, AccountId = varId))
```

### Model-Driven Apps
Model-driven apps are built directly on Dataverse tables.

**Key components:**
- **Tables** - Define the data structure
- **Forms** - UI for viewing/editing records
- **Views** - Lists of records with filters
- **Business rules** - Validation logic
- **Dashboards** - Analytics and charts

**Best practices:**
1. Design tables before building the app
2. Use business rules for validation
3. Create multiple views for different scenarios
4. Use security roles for access control

## Power Automate Integration

### Dataverse Triggers
```
When a row is added, modified or deleted
├── Table name: Accounts
├── Scope: Organization
└── Filter rows: statecode eq 0
```

### Dataverse Actions
```
// List rows
List rows
├── Table name: Accounts
├── Select columns: name,telephone1
├── Filter rows: statecode eq 0
└── Row count: 100

// Get a row by ID
Get a row by ID
├── Table name: Accounts
└── Row ID: @{triggerOutputs()?['body/accountid']}

// Add a new row
Add a new row
├── Table name: Accounts
└── Name: "New Account"

// Update a row
Update a row
├── Table name: Accounts
├── Row ID: @{variables('accountId')}
└── Name: "Updated Name"

// Delete a row
Delete a row
├── Table name: Accounts
└── Row ID: @{variables('accountId')}
```

### Flow Patterns

**Sync data from external system:**
```
HTTP Request received
    ↓
Parse JSON
    ↓
Apply to each (items)
    ↓
    ├── List rows (check if exists)
    ├── Condition (exists?)
    │   ├── Yes → Update a row
    │   └── No → Add a new row
```

**Send notification on record change:**
```
When a row is added (Accounts)
    ↓
Get a row by ID (Owner)
    ↓
Send an email (to Owner)
```

## Power BI Integration

### Direct Dataverse Connection
1. Get Data > Dataverse
2. Sign in with your account
3. Select tables
4. Load or Transform data

### Query Optimization
```
// Use query folding
let
    Source = CommonDataService.Database("https://yourorg.crm.dynamics.com"),
    accounts = Source{[Schema="dbo", Item="account"]}[Data],
    filtered = Table.SelectRows(accounts, each [statecode] = 0),
    selected = Table.SelectColumns(filtered, {"name", "revenue"})
in
    selected
```

### Best Practices for Power BI
1. **Use query folding** - Let Dataverse do filtering
2. **Limit columns** - Only import needed fields
3. **Use incremental refresh** - For large datasets
4. **Schedule refreshes** - During off-peak hours

## Python to Power Platform

### Call Power Automate from Python
```python
import requests

# HTTP trigger URL from Power Automate
flow_url = "https://prod-xx.westus.logic.azure.com/workflows/..."

# Trigger the flow
response = requests.post(flow_url, json={
    "account_name": "New Account",
    "source": "Python App"
})
```

### Sync Python App with Dataverse
```python
# Python app writes to Dataverse
# Power Automate flow triggers on change
# Sends notifications, updates other systems

client = get_client()
client.create("account", {"name": "From Python"})
# Power Automate flow handles the rest
```

## References

- See `references/power-apps.md` for Power Apps patterns
- See `references/power-automate.md` for flow examples
- See `references/power-bi.md` for reporting patterns
