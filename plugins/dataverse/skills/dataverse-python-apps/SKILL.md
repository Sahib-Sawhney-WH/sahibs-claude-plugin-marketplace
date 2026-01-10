# dataverse-python-apps

This skill provides guidance on building Python applications that use Microsoft Dataverse as a database. Use when users ask about "Python Dataverse app", "Flask Dataverse", "FastAPI Dataverse", "Dataverse backend", "Python API with Dataverse", "Dataverse data pipeline", or need help building Python applications with Dataverse.

## Architecture Patterns

### Basic Application Structure
```
my-dataverse-app/
├── app/
│   ├── __init__.py
│   ├── dataverse_client.py    # Dataverse connection
│   ├── models.py              # Data models
│   ├── services.py            # Business logic
│   └── api/
│       └── routes.py          # API endpoints
├── config.py
├── requirements.txt
└── main.py
```

### Singleton Client Pattern
```python
# dataverse_client.py
from PowerPlatform.Dataverse.client import DataverseClient
from azure.identity import ClientSecretCredential
import os

_client = None

def get_client() -> DataverseClient:
    global _client
    if _client is None:
        credential = ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"]
        )
        _client = DataverseClient(
            os.environ["DATAVERSE_URL"],
            credential
        )
    return _client
```

## Flask Integration

```python
from flask import Flask, jsonify, request
from dataverse_client import get_client

app = Flask(__name__)

@app.route('/accounts', methods=['GET'])
def list_accounts():
    client = get_client()
    pages = client.get(
        "account",
        select=["accountid", "name"],
        filter="statecode eq 0",
        top=100
    )
    accounts = []
    for page in pages:
        accounts.extend(page)
    return jsonify(accounts)

@app.route('/accounts', methods=['POST'])
def create_account():
    data = request.json
    client = get_client()
    ids = client.create("account", data)
    return jsonify({"id": ids[0]}), 201

@app.route('/accounts/<account_id>', methods=['GET'])
def get_account(account_id):
    client = get_client()
    account = client.get("account", account_id)
    return jsonify(account)
```

## FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from dataverse_client import get_client

app = FastAPI()

class AccountCreate(BaseModel):
    name: str
    telephone1: Optional[str] = None

class Account(BaseModel):
    accountid: str
    name: str
    telephone1: Optional[str]

@app.get("/accounts", response_model=List[Account])
async def list_accounts(top: int = 100):
    client = get_client()
    pages = client.get("account", select=["accountid", "name", "telephone1"], top=top)
    accounts = []
    for page in pages:
        accounts.extend(page)
    return accounts

@app.post("/accounts", response_model=dict)
async def create_account(account: AccountCreate):
    client = get_client()
    ids = client.create("account", account.model_dump(exclude_none=True))
    return {"id": ids[0]}

@app.get("/accounts/{account_id}", response_model=Account)
async def get_account(account_id: str):
    client = get_client()
    try:
        account = client.get("account", account_id)
        return account
    except Exception:
        raise HTTPException(status_code=404, detail="Account not found")
```

## Data Pipeline Pattern

```python
# ETL pipeline with Dataverse
from dataverse_client import get_client
import pandas as pd

def extract_accounts():
    """Extract accounts from Dataverse."""
    client = get_client()
    pages = client.get(
        "account",
        select=["accountid", "name", "revenue", "industrycode"],
        filter="statecode eq 0"
    )
    records = []
    for page in pages:
        records.extend(page)
    return pd.DataFrame(records)

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the data."""
    df['revenue_millions'] = df['revenue'] / 1_000_000
    df['has_revenue'] = df['revenue'] > 0
    return df

def load_to_dataverse(df: pd.DataFrame, table: str):
    """Load data back to Dataverse."""
    client = get_client()
    records = df.to_dict('records')
    ids = client.create(table, records)
    return ids

# Pipeline execution
def run_pipeline():
    df = extract_accounts()
    df = transform_data(df)
    # Save transformed data somewhere
    df.to_csv('accounts_processed.csv', index=False)
```

## Best Practices

1. **Use service principals** for production apps
2. **Reuse client instances** - expensive to create
3. **Handle errors gracefully** - wrap calls in try/except
4. **Use environment variables** for configuration
5. **Implement retry logic** for transient errors
6. **Limit query results** with select and top
7. **Use connection pooling** for high-throughput apps

## References

- See `references/flask-patterns.md` for Flask examples
- See `references/fastapi-patterns.md` for FastAPI examples
- See `references/pipeline-patterns.md` for data pipeline patterns
