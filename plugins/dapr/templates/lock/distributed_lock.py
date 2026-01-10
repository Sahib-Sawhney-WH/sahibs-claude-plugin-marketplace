"""
DAPR Distributed Lock Client Template
Building Block: Distributed Lock

Features:
- Acquire/release distributed locks
- Automatic expiry and renewal
- Context manager support
- Async/await patterns
"""
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from dapr.clients import DaprClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lock store name (from component YAML)
LOCK_STORE_NAME = "{{LOCK_STORE_NAME}}"


class DistributedLock:
    """
    Distributed lock using DAPR Lock building block.

    Provides mutual exclusion across distributed services.
    """

    def __init__(
        self,
        resource_id: str,
        store_name: str = LOCK_STORE_NAME,
        owner: Optional[str] = None,
        expiry_seconds: int = 60
    ):
        """
        Initialize a distributed lock.

        Args:
            resource_id: Unique identifier for the resource to lock
            store_name: DAPR lock store component name
            owner: Lock owner identifier (auto-generated if not provided)
            expiry_seconds: Lock expiry time in seconds
        """
        self.resource_id = resource_id
        self.store_name = store_name
        self.owner = owner or f"owner-{uuid.uuid4().hex[:8]}"
        self.expiry_seconds = expiry_seconds
        self._acquired = False
        self._renewal_task: Optional[asyncio.Task] = None

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire the lock.

        Args:
            timeout: Maximum time to wait for lock (None = no wait)

        Returns:
            True if lock acquired, False otherwise

        Example:
            lock = DistributedLock("order-123")
            if await lock.acquire():
                try:
                    # Critical section
                    pass
                finally:
                    await lock.release()
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            async with DaprClient() as client:
                response = await client.try_lock(
                    store_name=self.store_name,
                    resource_id=self.resource_id,
                    lock_owner=self.owner,
                    expiry_in_seconds=self.expiry_seconds
                )

                if response.success:
                    self._acquired = True
                    logger.info(f"Lock acquired: {self.resource_id} (owner: {self.owner})")
                    return True

            # Check timeout
            if timeout is None:
                return False

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                logger.warning(f"Lock timeout: {self.resource_id}")
                return False

            # Wait before retry
            await asyncio.sleep(0.1)

    async def release(self) -> bool:
        """
        Release the lock.

        Returns:
            True if lock released, False if not owned

        Example:
            await lock.release()
        """
        if not self._acquired:
            return False

        # Stop renewal if running
        if self._renewal_task:
            self._renewal_task.cancel()
            self._renewal_task = None

        async with DaprClient() as client:
            response = await client.unlock(
                store_name=self.store_name,
                resource_id=self.resource_id,
                lock_owner=self.owner
            )

            if response.status == 0:  # SUCCESS
                self._acquired = False
                logger.info(f"Lock released: {self.resource_id}")
                return True
            elif response.status == 1:  # LOCK_DOES_NOT_EXIST
                logger.warning(f"Lock not found: {self.resource_id}")
                return False
            elif response.status == 2:  # LOCK_BELONGS_TO_OTHERS
                logger.error(f"Lock owned by another: {self.resource_id}")
                return False

            return False

    async def start_renewal(self, interval_seconds: Optional[int] = None) -> None:
        """
        Start automatic lock renewal to prevent expiry during long operations.

        Args:
            interval_seconds: Renewal interval (default: half of expiry time)
        """
        if not self._acquired:
            raise RuntimeError("Cannot renew lock that is not acquired")

        interval = interval_seconds or (self.expiry_seconds // 2)

        async def renew_loop():
            while self._acquired:
                await asyncio.sleep(interval)
                if self._acquired:
                    # Re-acquire to extend expiry
                    async with DaprClient() as client:
                        response = await client.try_lock(
                            store_name=self.store_name,
                            resource_id=self.resource_id,
                            lock_owner=self.owner,
                            expiry_in_seconds=self.expiry_seconds
                        )
                        if response.success:
                            logger.debug(f"Lock renewed: {self.resource_id}")
                        else:
                            logger.warning(f"Lock renewal failed: {self.resource_id}")
                            self._acquired = False

        self._renewal_task = asyncio.create_task(renew_loop())

    @property
    def is_acquired(self) -> bool:
        """Check if lock is currently held."""
        return self._acquired


@asynccontextmanager
async def distributed_lock(
    resource_id: str,
    store_name: str = LOCK_STORE_NAME,
    timeout: Optional[float] = None,
    expiry_seconds: int = 60,
    auto_renew: bool = False
):
    """
    Context manager for distributed locking.

    Args:
        resource_id: Resource to lock
        store_name: Lock store name
        timeout: Max wait time for lock
        expiry_seconds: Lock expiry time
        auto_renew: Enable automatic renewal

    Example:
        async with distributed_lock("order-123", timeout=10):
            # Critical section - only one instance executes this
            await process_order()

    Raises:
        RuntimeError: If lock cannot be acquired within timeout
    """
    lock = DistributedLock(
        resource_id=resource_id,
        store_name=store_name,
        expiry_seconds=expiry_seconds
    )

    acquired = await lock.acquire(timeout=timeout)
    if not acquired:
        raise RuntimeError(f"Failed to acquire lock: {resource_id}")

    try:
        if auto_renew:
            await lock.start_renewal()
        yield lock
    finally:
        await lock.release()


# =============================================================================
# FastAPI Integration Example
# =============================================================================

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Distributed Lock Service")


@app.post("/orders/{order_id}/process")
async def process_order(order_id: str):
    """Process an order with distributed locking."""
    try:
        async with distributed_lock(
            f"order-{order_id}",
            timeout=30,
            auto_renew=True
        ):
            # Only one instance processes this order at a time
            logger.info(f"Processing order: {order_id}")

            # Simulate processing
            await asyncio.sleep(5)

            return {"order_id": order_id, "status": "processed"}

    except RuntimeError as e:
        raise HTTPException(status_code=423, detail=str(e))


@app.post("/inventory/{product_id}/update")
async def update_inventory(product_id: str, quantity: int):
    """Update inventory with distributed lock."""
    async with distributed_lock(f"inventory-{product_id}", timeout=10):
        # Read current inventory
        # Update quantity
        # Save changes
        logger.info(f"Updated inventory for {product_id}: {quantity}")
        return {"product_id": product_id, "quantity": quantity}


# =============================================================================
# CLI Usage Example
# =============================================================================

if __name__ == "__main__":
    async def main():
        # Simple lock usage
        lock = DistributedLock("my-resource")

        if await lock.acquire(timeout=5):
            try:
                print("Lock acquired! Doing work...")
                await asyncio.sleep(2)
            finally:
                await lock.release()
        else:
            print("Could not acquire lock")

        # Context manager usage
        async with distributed_lock("another-resource", timeout=10):
            print("Working with lock...")
            await asyncio.sleep(1)

        print("Done!")

    asyncio.run(main())
