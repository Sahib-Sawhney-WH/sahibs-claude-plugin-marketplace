"""
HTTP Request Tool

Tool for making HTTP requests from DAPR Agents.
Supports REST APIs, webhooks, and external service integration.
Uses DAPR service invocation when available for reliability.
"""

from dapr_agents import tool, AssistantAgent
from dapr.clients import DaprClient
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, Literal
import httpx
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Input Models
# =============================================================================

class HttpRequestInput(BaseModel):
    """Input for HTTP request tool."""
    url: str = Field(..., description="Target URL")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        default="GET",
        description="HTTP method"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Request headers"
    )
    body: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Request body (for POST/PUT/PATCH)"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout in seconds"
    )


class DaprServiceInput(BaseModel):
    """Input for DAPR service invocation."""
    app_id: str = Field(..., description="Target DAPR app ID")
    method_name: str = Field(..., description="Method/endpoint to invoke")
    http_method: Literal["GET", "POST", "PUT", "DELETE"] = Field(default="POST")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Request data")


# =============================================================================
# Direct HTTP Tools
# =============================================================================

@tool
async def http_get(url: str) -> str:
    """
    Make a GET request to a URL.

    Args:
        url: The URL to fetch

    Returns:
        Response body as string
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        return response.text[:10000]  # Limit response size


@tool
async def http_post(url: str, data: dict) -> str:
    """
    Make a POST request with JSON data.

    Args:
        url: The target URL
        data: JSON data to send

    Returns:
        Response body as string
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.text[:10000]


@tool
async def http_request(input: HttpRequestInput) -> str:
    """
    Make a configurable HTTP request.

    Args:
        input: Request configuration with URL, method, headers, body

    Returns:
        Response details including status and body
    """
    async with httpx.AsyncClient() as client:
        kwargs = {
            "url": input.url,
            "method": input.method,
            "timeout": input.timeout,
        }

        if input.headers:
            kwargs["headers"] = input.headers

        if input.body and input.method in ["POST", "PUT", "PATCH"]:
            kwargs["json"] = input.body

        response = await client.request(**kwargs)

        return json.dumps({
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text[:5000]
        }, indent=2)


# =============================================================================
# DAPR Service Invocation Tools
# =============================================================================

@tool
async def invoke_dapr_service(input: DaprServiceInput) -> str:
    """
    Invoke another DAPR service with built-in retry and circuit breaker.

    Args:
        input: Service invocation parameters

    Returns:
        Service response
    """
    async with DaprClient() as client:
        if input.http_method == "GET":
            response = await client.invoke_method(
                app_id=input.app_id,
                method_name=input.method_name,
                http_verb="GET"
            )
        else:
            response = await client.invoke_method(
                app_id=input.app_id,
                method_name=input.method_name,
                data=json.dumps(input.data) if input.data else None,
                http_verb=input.http_method,
                content_type="application/json"
            )

        return response.text() if hasattr(response, 'text') else str(response)


@tool
async def invoke_service_method(app_id: str, method: str, data: Optional[dict] = None) -> str:
    """
    Simple service invocation helper.

    Args:
        app_id: Target DAPR application ID
        method: Method/endpoint name
        data: Optional data to send

    Returns:
        Service response
    """
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id=app_id,
            method_name=method,
            data=json.dumps(data) if data else None,
            http_verb="POST" if data else "GET",
            content_type="application/json"
        )
        return str(response.data) if response.data else "Success"


# =============================================================================
# Webhook Tools
# =============================================================================

@tool
async def send_webhook(
    url: str,
    event_type: str,
    payload: dict,
    secret: Optional[str] = None
) -> str:
    """
    Send a webhook notification.

    Args:
        url: Webhook URL
        event_type: Type of event (e.g., "order.created")
        payload: Event payload data
        secret: Optional secret for HMAC signature

    Returns:
        Webhook delivery status
    """
    import hashlib
    import hmac

    headers = {
        "Content-Type": "application/json",
        "X-Event-Type": event_type,
    }

    body = json.dumps(payload)

    if secret:
        signature = hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            content=body,
            headers=headers,
            timeout=30
        )

        return json.dumps({
            "delivered": response.status_code < 400,
            "status_code": response.status_code,
            "response": response.text[:500]
        })


# =============================================================================
# API Client Tools
# =============================================================================

class APIClientConfig(BaseModel):
    """Configuration for API client."""
    base_url: str
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    default_headers: Optional[Dict[str, str]] = None


class APIClient:
    """Reusable API client with authentication."""

    def __init__(self, config: APIClientConfig):
        self.config = config
        self.headers = config.default_headers or {}

        if config.api_key:
            self.headers["X-API-Key"] = config.api_key
        if config.bearer_token:
            self.headers["Authorization"] = f"Bearer {config.bearer_token}"

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make an API request."""
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            try:
                return response.json()
            except json.JSONDecodeError:
                return {"text": response.text}


def create_api_tool(
    name: str,
    client: APIClient,
    method: str,
    path: str,
    description: str
):
    """
    Factory to create API-specific tools.

    Example:
        client = APIClient(APIClientConfig(base_url="https://api.example.com"))
        get_users = create_api_tool("get_users", client, "GET", "/users", "Get all users")
    """
    @tool
    async def api_tool(**kwargs) -> str:
        result = await client.request(method, path, data=kwargs if method != "GET" else None)
        return json.dumps(result, indent=2)

    api_tool.__name__ = name
    api_tool.__doc__ = description

    return api_tool


# =============================================================================
# Example Agent with HTTP Tools
# =============================================================================

def create_http_agent() -> AssistantAgent:
    """Create an agent with HTTP tools."""
    return AssistantAgent(
        name="http-agent",
        role="HTTP Request Agent",
        instructions="""You can make HTTP requests and invoke DAPR services.
        Use http_get for simple GET requests.
        Use http_post for POST requests with data.
        Use http_request for advanced configurations.
        Use invoke_dapr_service for calling other DAPR services.""",
        tools=[
            http_get,
            http_post,
            http_request,
            invoke_dapr_service,
            invoke_service_method,
            send_webhook,
        ],
        model="gpt-4o"
    )


# =============================================================================
# Usage Example
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def demo():
        agent = create_http_agent()

        # Example: Fetch data from an API
        result = await agent.run(
            "Fetch the latest posts from https://jsonplaceholder.typicode.com/posts?_limit=3"
        )
        print(result)

    asyncio.run(demo())
