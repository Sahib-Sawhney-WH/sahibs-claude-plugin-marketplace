# Dataverse Error Handling

## Exception Hierarchy

```python
from PowerPlatform.Dataverse.core.errors import (
    HttpError,          # HTTP-level errors (4xx, 5xx)
    MetadataError,      # Table/column metadata errors
    ValidationError,    # Input validation errors
)
```

## HttpError

Raised for HTTP-level failures from the Dataverse API.

```python
from PowerPlatform.Dataverse.core.errors import HttpError

try:
    client.get("account", "invalid-guid")
except HttpError as e:
    print(f"Status: {e.status_code}")
    print(f"Message: {e.message}")
    print(f"Error Code: {e.code}")
    print(f"Subcode: {e.subcode}")
    print(f"Is Transient: {e.is_transient}")
```

### Common HTTP Error Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 400 | Bad Request | Check request format/data |
| 401 | Unauthorized | Check credentials/permissions |
| 403 | Forbidden | Check security role permissions |
| 404 | Not Found | Record or table doesn't exist |
| 409 | Conflict | Concurrent modification conflict |
| 429 | Too Many Requests | Rate limited - retry with backoff |
| 500 | Server Error | Transient - retry |
| 503 | Service Unavailable | Transient - retry |

### Transient vs Non-Transient Errors

```python
try:
    result = client.create("account", data)
except HttpError as e:
    if e.is_transient:
        # Safe to retry: 429, 500, 503, etc.
        print("Transient error - retrying...")
        time.sleep(5)
        result = client.create("account", data)
    else:
        # Don't retry: 400, 401, 403, 404
        print(f"Permanent error: {e.message}")
        raise
```

## MetadataError

Raised for table/column metadata operations.

```python
from PowerPlatform.Dataverse.core.errors import MetadataError

try:
    client.create_table("new_mytable", {"new_name": "string"})
except MetadataError as e:
    print(f"Metadata error: {e.message}")
    # Common causes:
    # - Table already exists
    # - Invalid column type
    # - Missing required prefix
```

## ValidationError

Raised for input validation failures.

```python
from PowerPlatform.Dataverse.core.errors import ValidationError

try:
    client.create("account", {"invalid_field": "value"})
except ValidationError as e:
    print(f"Validation error: {e.message}")
```

## Retry Pattern with Exponential Backoff

```python
import time

def backoff(operation, delays=(0, 2, 5, 10, 20)):
    """Execute operation with exponential backoff."""
    last_error = None
    total_waited = 0

    for delay in delays:
        if delay:
            time.sleep(delay)
            total_waited += delay

        try:
            return operation()
        except HttpError as e:
            if not e.is_transient:
                raise  # Don't retry non-transient errors
            last_error = e
            print(f"Transient error, retrying in {delay}s...")
        except Exception as e:
            last_error = e

    if last_error:
        raise last_error

# Usage
result = backoff(lambda: client.create("account", data))
```

## Rate Limiting Handling

```python
import time
from PowerPlatform.Dataverse.core.errors import HttpError

def rate_limited_operation(operation, max_retries=5):
    """Handle rate limiting (429) errors."""
    for attempt in range(max_retries):
        try:
            return operation()
        except HttpError as e:
            if e.status_code == 429:
                # Get retry-after header if available
                retry_after = getattr(e, 'retry_after', 60)
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                raise
    raise Exception("Max retries exceeded")
```

## Comprehensive Error Handling Example

```python
from PowerPlatform.Dataverse.core.errors import HttpError, MetadataError, ValidationError

def safe_create_record(client, table, data):
    """Create record with comprehensive error handling."""
    try:
        ids = client.create(table, data)
        return {"success": True, "id": ids[0]}

    except ValidationError as e:
        return {
            "success": False,
            "error_type": "validation",
            "message": str(e),
            "action": "Check input data format and required fields"
        }

    except HttpError as e:
        if e.status_code == 401:
            return {
                "success": False,
                "error_type": "authentication",
                "message": "Authentication failed",
                "action": "Check credentials and re-authenticate"
            }
        elif e.status_code == 403:
            return {
                "success": False,
                "error_type": "authorization",
                "message": "Permission denied",
                "action": f"Check security role for {table} create permission"
            }
        elif e.status_code == 404:
            return {
                "success": False,
                "error_type": "not_found",
                "message": f"Table '{table}' not found",
                "action": "Verify table name and that it exists"
            }
        elif e.is_transient:
            return {
                "success": False,
                "error_type": "transient",
                "message": str(e),
                "action": "Retry the operation"
            }
        else:
            return {
                "success": False,
                "error_type": "http",
                "status": e.status_code,
                "message": str(e)
            }

    except Exception as e:
        return {
            "success": False,
            "error_type": "unknown",
            "message": str(e)
        }
```

## Logging Errors

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dataverse")

def logged_operation(operation, context="operation"):
    """Execute operation with logging."""
    try:
        result = operation()
        logger.info(f"{context} succeeded")
        return result
    except HttpError as e:
        logger.error(
            f"{context} failed: HTTP {e.status_code} - {e.message}",
            extra={
                "error_code": e.code,
                "is_transient": e.is_transient
            }
        )
        raise
    except Exception as e:
        logger.exception(f"{context} failed with unexpected error")
        raise
```

## Best Practices

1. **Always handle HttpError** - Most common exception type
2. **Check is_transient** - Only retry transient errors
3. **Use exponential backoff** - Don't hammer the API on failures
4. **Log error details** - Include status code, error code, message
5. **Don't catch generic Exception** - Let unexpected errors propagate
6. **Handle 401/403 specially** - May need re-authentication or permission changes
