#!/usr/bin/env python3
"""
Dataverse MCP Server

A Model Context Protocol server that provides tools for interacting with
Microsoft Dataverse using the PowerPlatform-Dataverse-Client SDK.

Tools provided:
- dataverse_connect: Establish connection with chosen auth method
- dataverse_list_tables: List all tables in environment
- dataverse_get_table_info: Get schema/columns for a table
- dataverse_query: Query records with OData or SQL
- dataverse_get_record: Get single record by ID
- dataverse_create_record: Create single record
- dataverse_create_records: Bulk create records
- dataverse_update_record: Update single record
- dataverse_delete_record: Delete single record
- dataverse_create_table: Create new table with schema
- dataverse_create_column: Add column to table
- dataverse_upload_file: Upload file to file column
- dataverse_download_file: Download file from record
"""

import os
import sys
import json
import asyncio
from typing import Any, Optional
from contextlib import asynccontextmanager

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: MCP library not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Dataverse SDK imports
try:
    from PowerPlatform.Dataverse.client import DataverseClient
    from PowerPlatform.Dataverse.core.errors import HttpError, MetadataError, ValidationError
except ImportError:
    print("Error: PowerPlatform-Dataverse-Client not installed. Run: pip install PowerPlatform-Dataverse-Client", file=sys.stderr)
    sys.exit(1)

# Azure Identity imports
try:
    from azure.identity import (
        InteractiveBrowserCredential,
        DeviceCodeCredential,
        ClientSecretCredential,
    )
except ImportError:
    print("Error: azure-identity not installed. Run: pip install azure-identity", file=sys.stderr)
    sys.exit(1)


# Global client instance
_client: Optional[DataverseClient] = None
_connection_info: dict = {}


def get_client() -> DataverseClient:
    """Get the current Dataverse client, raising error if not connected."""
    if _client is None:
        raise RuntimeError("Not connected to Dataverse. Use dataverse_connect first.")
    return _client


def format_error(e: Exception) -> dict:
    """Format exception into error response."""
    error_info = {
        "error": str(e),
        "type": type(e).__name__,
    }
    if isinstance(e, HttpError):
        error_info["status_code"] = getattr(e, "status_code", None)
        error_info["code"] = getattr(e, "code", None)
        error_info["is_transient"] = getattr(e, "is_transient", False)
    return error_info


# Tool implementations

async def connect(
    base_url: str,
    auth_method: str = "interactive",
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> dict:
    """Connect to a Dataverse environment."""
    global _client, _connection_info

    try:
        # Create credential based on auth method
        if auth_method == "interactive":
            credential = InteractiveBrowserCredential()
        elif auth_method == "device_code":
            credential = DeviceCodeCredential()
        elif auth_method == "client_secret":
            if not all([tenant_id, client_id, client_secret]):
                return {"error": "client_secret auth requires tenant_id, client_id, and client_secret"}
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            return {"error": f"Unknown auth_method: {auth_method}. Use: interactive, device_code, client_secret"}

        # Create client
        base_url = base_url.rstrip("/")
        _client = DataverseClient(base_url, credential)

        # Test connection by listing tables
        tables = _client.list_tables()

        _connection_info = {
            "base_url": base_url,
            "auth_method": auth_method,
            "table_count": len(tables),
        }

        return {
            "success": True,
            "message": f"Connected to {base_url}",
            "table_count": len(tables),
        }

    except Exception as e:
        _client = None
        return format_error(e)


async def list_tables() -> dict:
    """List all tables in the Dataverse environment."""
    try:
        client = get_client()
        tables = client.list_tables()
        return {
            "success": True,
            "count": len(tables),
            "tables": tables[:100],  # Limit to first 100 for readability
            "truncated": len(tables) > 100,
        }
    except Exception as e:
        return format_error(e)


async def get_table_info(table_schema_name: str) -> dict:
    """Get detailed information about a table."""
    try:
        client = get_client()
        info = client.get_table_info(table_schema_name)
        if info:
            return {"success": True, "table_info": info}
        else:
            return {"success": False, "error": f"Table '{table_schema_name}' not found"}
    except Exception as e:
        return format_error(e)


async def query(
    table_schema_name: str,
    select: Optional[list] = None,
    filter: Optional[str] = None,
    orderby: Optional[list] = None,
    top: Optional[int] = None,
    expand: Optional[list] = None,
) -> dict:
    """Query records from a table using OData."""
    try:
        client = get_client()

        # Build query parameters
        kwargs = {}
        if select:
            kwargs["select"] = select
        if filter:
            kwargs["filter"] = filter
        if orderby:
            kwargs["orderby"] = orderby
        if top:
            kwargs["top"] = top
        if expand:
            kwargs["expand"] = expand

        # Execute query
        records = []
        pages = client.get(table_schema_name, **kwargs)
        for page in pages:
            records.extend(page)
            if len(records) >= (top or 1000):
                break

        return {
            "success": True,
            "count": len(records),
            "records": records[:top] if top else records,
        }
    except Exception as e:
        return format_error(e)


async def query_sql(sql: str) -> dict:
    """Execute a SQL query (read-only)."""
    try:
        client = get_client()
        results = client.query_sql(sql)
        return {
            "success": True,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        return format_error(e)


async def get_record(table_schema_name: str, record_id: str, select: Optional[list] = None) -> dict:
    """Get a single record by ID."""
    try:
        client = get_client()
        kwargs = {}
        if select:
            kwargs["select"] = select
        record = client.get(table_schema_name, record_id, **kwargs)
        return {"success": True, "record": record}
    except Exception as e:
        return format_error(e)


async def create_record(table_schema_name: str, data: dict) -> dict:
    """Create a single record."""
    try:
        client = get_client()
        ids = client.create(table_schema_name, data)
        return {
            "success": True,
            "record_id": ids[0] if ids else None,
            "message": f"Created record in {table_schema_name}",
        }
    except Exception as e:
        return format_error(e)


async def create_records(table_schema_name: str, records: list) -> dict:
    """Create multiple records (bulk create)."""
    try:
        client = get_client()
        ids = client.create(table_schema_name, records)
        return {
            "success": True,
            "record_ids": ids,
            "count": len(ids),
            "message": f"Created {len(ids)} records in {table_schema_name}",
        }
    except Exception as e:
        return format_error(e)


async def update_record(table_schema_name: str, record_id: str, data: dict) -> dict:
    """Update a single record."""
    try:
        client = get_client()
        client.update(table_schema_name, record_id, data)
        return {
            "success": True,
            "message": f"Updated record {record_id} in {table_schema_name}",
        }
    except Exception as e:
        return format_error(e)


async def delete_record(table_schema_name: str, record_id: str) -> dict:
    """Delete a single record."""
    try:
        client = get_client()
        client.delete(table_schema_name, record_id)
        return {
            "success": True,
            "message": f"Deleted record {record_id} from {table_schema_name}",
        }
    except Exception as e:
        return format_error(e)


async def create_table(
    table_schema_name: str,
    columns: dict,
    primary_column_schema_name: Optional[str] = None,
    solution_unique_name: Optional[str] = None,
) -> dict:
    """Create a new custom table."""
    try:
        client = get_client()
        kwargs = {"columns": columns}
        if primary_column_schema_name:
            kwargs["primary_column_schema_name"] = primary_column_schema_name
        if solution_unique_name:
            kwargs["solution_unique_name"] = solution_unique_name

        info = client.create_table(table_schema_name, **kwargs)
        return {
            "success": True,
            "table_info": info,
            "message": f"Created table {table_schema_name}",
        }
    except Exception as e:
        return format_error(e)


async def create_column(table_schema_name: str, columns: dict) -> dict:
    """Add columns to an existing table."""
    try:
        client = get_client()
        created = client.create_columns(table_schema_name, columns)
        return {
            "success": True,
            "columns_created": created,
            "message": f"Added {len(created)} column(s) to {table_schema_name}",
        }
    except Exception as e:
        return format_error(e)


async def upload_file(
    table_schema_name: str,
    record_id: str,
    file_attribute: str,
    file_path: str,
    mode: str = "small",
) -> dict:
    """Upload a file to a file column."""
    try:
        client = get_client()
        client.upload_file(
            table_schema_name=table_schema_name,
            record_id=record_id,
            file_name_attribute=file_attribute,
            path=file_path,
            mode=mode,
        )
        return {
            "success": True,
            "message": f"Uploaded file to {table_schema_name}/{record_id}/{file_attribute}",
        }
    except Exception as e:
        return format_error(e)


async def download_file(
    table_schema_name: str,
    record_id: str,
    file_attribute: str,
    output_path: str,
) -> dict:
    """Download a file from a file column."""
    try:
        client = get_client()
        # Get entity set name
        table_info = client.get_table_info(table_schema_name)
        if not table_info:
            return {"error": f"Table '{table_schema_name}' not found"}

        entity_set = table_info.get("entity_set_name")
        odata = client._get_odata()

        # Download file
        url = f"{odata.api}/{entity_set}({record_id})/{file_attribute}/$value"
        response = odata._request("get", url)

        # Save to file
        with open(output_path, "wb") as f:
            f.write(response.content)

        return {
            "success": True,
            "message": f"Downloaded file to {output_path}",
            "size_bytes": len(response.content),
        }
    except Exception as e:
        return format_error(e)


# MCP Server setup

app = Server("dataverse")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="dataverse_connect",
            description="Connect to a Microsoft Dataverse environment",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_url": {
                        "type": "string",
                        "description": "Dataverse environment URL (e.g., https://yourorg.crm.dynamics.com)",
                    },
                    "auth_method": {
                        "type": "string",
                        "enum": ["interactive", "device_code", "client_secret"],
                        "default": "interactive",
                        "description": "Authentication method to use",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID (required for client_secret auth)",
                    },
                    "client_id": {
                        "type": "string",
                        "description": "Azure client/app ID (required for client_secret auth)",
                    },
                    "client_secret": {
                        "type": "string",
                        "description": "Azure client secret (required for client_secret auth)",
                    },
                },
                "required": ["base_url"],
            },
        ),
        Tool(
            name="dataverse_list_tables",
            description="List all tables in the connected Dataverse environment",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="dataverse_get_table_info",
            description="Get detailed schema information about a Dataverse table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name (e.g., 'account', 'contact', 'new_MyCustomTable')",
                    },
                },
                "required": ["table_schema_name"],
            },
        ),
        Tool(
            name="dataverse_query",
            description="Query records from a Dataverse table using OData",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name to query",
                    },
                    "select": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Columns to return",
                    },
                    "filter": {
                        "type": "string",
                        "description": "OData filter expression (e.g., 'statecode eq 0')",
                    },
                    "orderby": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sort columns (e.g., ['name asc', 'createdon desc'])",
                    },
                    "top": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                    },
                    "expand": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Navigation properties to expand",
                    },
                },
                "required": ["table_schema_name"],
            },
        ),
        Tool(
            name="dataverse_query_sql",
            description="Execute a read-only SQL query against Dataverse",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL query (e.g., 'SELECT TOP 10 name FROM account WHERE statecode = 0')",
                    },
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="dataverse_get_record",
            description="Get a single record by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record GUID",
                    },
                    "select": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Columns to return",
                    },
                },
                "required": ["table_schema_name", "record_id"],
            },
        ),
        Tool(
            name="dataverse_create_record",
            description="Create a new record in a Dataverse table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "data": {
                        "type": "object",
                        "description": "Record data as key-value pairs",
                    },
                },
                "required": ["table_schema_name", "data"],
            },
        ),
        Tool(
            name="dataverse_create_records",
            description="Create multiple records in a Dataverse table (bulk create)",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "records": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of record data objects",
                    },
                },
                "required": ["table_schema_name", "records"],
            },
        ),
        Tool(
            name="dataverse_update_record",
            description="Update an existing record",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record GUID to update",
                    },
                    "data": {
                        "type": "object",
                        "description": "Fields to update",
                    },
                },
                "required": ["table_schema_name", "record_id", "data"],
            },
        ),
        Tool(
            name="dataverse_delete_record",
            description="Delete a record from Dataverse",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record GUID to delete",
                    },
                },
                "required": ["table_schema_name", "record_id"],
            },
        ),
        Tool(
            name="dataverse_create_table",
            description="Create a new custom table in Dataverse",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name (must include prefix, e.g., 'new_MyTable')",
                    },
                    "columns": {
                        "type": "object",
                        "description": "Column definitions as {column_name: type}. Types: string, int, decimal, bool, datetime",
                    },
                    "primary_column_schema_name": {
                        "type": "string",
                        "description": "Custom primary column name (optional)",
                    },
                    "solution_unique_name": {
                        "type": "string",
                        "description": "Solution to add table to (optional)",
                    },
                },
                "required": ["table_schema_name", "columns"],
            },
        ),
        Tool(
            name="dataverse_create_column",
            description="Add columns to an existing Dataverse table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "columns": {
                        "type": "object",
                        "description": "Column definitions as {column_name: type}",
                    },
                },
                "required": ["table_schema_name", "columns"],
            },
        ),
        Tool(
            name="dataverse_upload_file",
            description="Upload a file to a Dataverse file column",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record GUID",
                    },
                    "file_attribute": {
                        "type": "string",
                        "description": "File column logical name",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to upload",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["small", "chunk"],
                        "default": "small",
                        "description": "Upload mode: 'small' for <128MB, 'chunk' for large files",
                    },
                },
                "required": ["table_schema_name", "record_id", "file_attribute", "file_path"],
            },
        ),
        Tool(
            name="dataverse_download_file",
            description="Download a file from a Dataverse file column",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_schema_name": {
                        "type": "string",
                        "description": "Table schema name",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record GUID",
                    },
                    "file_attribute": {
                        "type": "string",
                        "description": "File column logical name",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save the downloaded file",
                    },
                },
                "required": ["table_schema_name", "record_id", "file_attribute", "output_path"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    # Route to appropriate function
    if name == "dataverse_connect":
        result = await connect(**arguments)
    elif name == "dataverse_list_tables":
        result = await list_tables()
    elif name == "dataverse_get_table_info":
        result = await get_table_info(**arguments)
    elif name == "dataverse_query":
        result = await query(**arguments)
    elif name == "dataverse_query_sql":
        result = await query_sql(**arguments)
    elif name == "dataverse_get_record":
        result = await get_record(**arguments)
    elif name == "dataverse_create_record":
        result = await create_record(**arguments)
    elif name == "dataverse_create_records":
        result = await create_records(**arguments)
    elif name == "dataverse_update_record":
        result = await update_record(**arguments)
    elif name == "dataverse_delete_record":
        result = await delete_record(**arguments)
    elif name == "dataverse_create_table":
        result = await create_table(**arguments)
    elif name == "dataverse_create_column":
        result = await create_column(**arguments)
    elif name == "dataverse_upload_file":
        result = await upload_file(**arguments)
    elif name == "dataverse_download_file":
        result = await download_file(**arguments)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
