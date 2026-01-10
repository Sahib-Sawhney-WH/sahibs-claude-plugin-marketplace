"""
DAPR Configuration Client Template
Building Block: Configuration

Features:
- Get configuration values
- Subscribe to configuration changes
- Watch for real-time updates
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from dapr.clients import DaprClient
from dapr.clients.grpc._response import ConfigurationResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration store name (from component YAML)
CONFIG_STORE_NAME = "{{CONFIG_STORE_NAME}}"


class ConfigurationClient:
    """Client for DAPR Configuration building block."""

    def __init__(self, store_name: str = CONFIG_STORE_NAME):
        self.store_name = store_name
        self._subscriptions: Dict[str, asyncio.Task] = {}

    async def get(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get configuration values for specified keys.

        Args:
            keys: List of configuration keys to retrieve

        Returns:
            Dictionary of key-value pairs

        Example:
            config = await client.get(["database.host", "database.port"])
            print(config["database.host"])
        """
        async with DaprClient() as client:
            response: ConfigurationResponse = await client.get_configuration(
                store_name=self.store_name,
                keys=keys
            )

            result = {}
            for key, item in response.items.items():
                result[key] = item.value
                logger.debug(f"Config [{key}]: {item.value} (version: {item.version})")

            return result

    async def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values from the store.

        Returns:
            Dictionary of all key-value pairs
        """
        async with DaprClient() as client:
            response: ConfigurationResponse = await client.get_configuration(
                store_name=self.store_name,
                keys=[]  # Empty list returns all
            )

            return {key: item.value for key, item in response.items.items()}

    async def subscribe(
        self,
        keys: List[str],
        callback: Callable[[str, str], None]
    ) -> str:
        """
        Subscribe to configuration changes.

        Args:
            keys: List of keys to watch
            callback: Function called when config changes (key, new_value)

        Returns:
            Subscription ID for unsubscribing

        Example:
            def on_change(key: str, value: str):
                print(f"Config changed: {key} = {value}")

            sub_id = await client.subscribe(["feature.enabled"], on_change)
        """
        async with DaprClient() as client:
            subscription_id = await client.subscribe_configuration(
                store_name=self.store_name,
                keys=keys
            )

            # Start watching for changes
            async def watch():
                async for items in client.watch_configuration(
                    store_name=self.store_name,
                    subscription_id=subscription_id
                ):
                    for key, item in items.items():
                        logger.info(f"Config update: {key} = {item.value}")
                        callback(key, item.value)

            task = asyncio.create_task(watch())
            self._subscriptions[subscription_id] = task

            logger.info(f"Subscribed to config changes: {keys}")
            return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from configuration changes.

        Args:
            subscription_id: The subscription ID returned from subscribe()
        """
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].cancel()
            del self._subscriptions[subscription_id]

        async with DaprClient() as client:
            await client.unsubscribe_configuration(
                store_name=self.store_name,
                subscription_id=subscription_id
            )
            logger.info(f"Unsubscribed: {subscription_id}")


# =============================================================================
# FastAPI Integration Example
# =============================================================================

from fastapi import FastAPI, BackgroundTasks

app = FastAPI(title="Configuration Service")
config_client = ConfigurationClient()

# Cache for configuration values
_config_cache: Dict[str, str] = {}


@app.on_event("startup")
async def startup():
    """Load initial configuration and subscribe to changes."""
    # Load initial config
    global _config_cache
    _config_cache = await config_client.get_all()
    logger.info(f"Loaded {len(_config_cache)} config values")

    # Subscribe to changes
    def update_cache(key: str, value: str):
        _config_cache[key] = value

    await config_client.subscribe(
        keys=list(_config_cache.keys()),
        callback=update_cache
    )


@app.get("/config/{key}")
async def get_config(key: str):
    """Get a configuration value."""
    if key in _config_cache:
        return {"key": key, "value": _config_cache[key], "source": "cache"}

    # Fallback to direct fetch
    config = await config_client.get([key])
    return {"key": key, "value": config.get(key), "source": "store"}


@app.get("/config")
async def get_all_config():
    """Get all configuration values."""
    return _config_cache


# =============================================================================
# CLI Usage Example
# =============================================================================

if __name__ == "__main__":
    async def main():
        client = ConfigurationClient()

        # Get specific keys
        config = await client.get(["app.name", "app.version"])
        print(f"App config: {config}")

        # Get all configuration
        all_config = await client.get_all()
        print(f"All config: {all_config}")

        # Subscribe to changes (runs until cancelled)
        def on_change(key: str, value: str):
            print(f"Changed: {key} = {value}")

        sub_id = await client.subscribe(["feature.enabled"], on_change)

        # Keep running to receive updates
        try:
            await asyncio.sleep(3600)  # Run for 1 hour
        finally:
            await client.unsubscribe(sub_id)

    asyncio.run(main())
