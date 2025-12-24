"""
DAPR Pluggable State Store Component
====================================

Implement a custom state store using gRPC protocol.
DAPR communicates with this component via Unix Domain Socket.

Requirements:
    pip install dapr-ext-grpc grpcio grpcio-tools

Usage:
    1. Implement the StateStore interface methods
    2. Build and run as a container or process
    3. Register with DAPR using component.yaml

Proto definitions: https://github.com/dapr/dapr/tree/master/dapr/proto
"""

import json
import logging
from concurrent import futures
from typing import Any, Dict, List, Optional

import grpc

# Import generated proto stubs (generate from DAPR protos)
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. dapr/proto/components/v1/*.proto
from dapr.proto.components.v1 import state_pb2
from dapr.proto.components.v1 import state_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomStateStore(state_pb2_grpc.StateStoreServicer):
    """
    Custom State Store Implementation.

    Implement these methods to create your own state store:
    - Init: Initialize the component with metadata
    - Features: Declare supported features
    - Get: Retrieve a single value
    - BulkGet: Retrieve multiple values
    - Set: Store a single value
    - BulkSet: Store multiple values
    - Delete: Remove a single value
    - BulkDelete: Remove multiple values
    """

    def __init__(self):
        # Your storage backend (replace with actual implementation)
        self._store: Dict[str, bytes] = {}
        self._etags: Dict[str, str] = {}
        self._metadata: Dict[str, str] = {}

    def Init(self, request: state_pb2.InitRequest, context) -> state_pb2.InitResponse:
        """
        Initialize the state store with configuration metadata.

        Args:
            request: Contains metadata from component YAML
        """
        logger.info("Initializing custom state store")

        # Extract configuration from metadata
        for item in request.metadata.properties:
            self._metadata[item.key] = item.value

        # Example: Connect to your storage backend
        # connection_string = self._metadata.get("connectionString")
        # self._client = MyStorageClient(connection_string)

        return state_pb2.InitResponse()

    def Features(self, request: state_pb2.FeaturesRequest, context) -> state_pb2.FeaturesResponse:
        """
        Declare which features this state store supports.

        Features:
        - ETAG: Optimistic concurrency control
        - TRANSACTIONAL: Multi-operation transactions
        - TTL: Time-to-live for entries
        - DELETE_WITH_PREFIX: Bulk delete by prefix
        - ACTOR: Actor state operations
        - QUERY_API: Query filtering support
        """
        return state_pb2.FeaturesResponse(
            features=[
                "ETAG",
                "TRANSACTIONAL",
                # "TTL",
                # "QUERY_API",
            ]
        )

    def Get(self, request: state_pb2.GetRequest, context) -> state_pb2.GetResponse:
        """
        Retrieve a single state value by key.
        """
        key = request.key
        logger.debug(f"Get: {key}")

        if key not in self._store:
            return state_pb2.GetResponse()

        return state_pb2.GetResponse(
            data=self._store[key],
            etag=self._etags.get(key, ""),
            # content_type="application/json",
        )

    def BulkGet(self, request: state_pb2.BulkGetRequest, context) -> state_pb2.BulkGetResponse:
        """
        Retrieve multiple state values.
        """
        items = []
        for item in request.items:
            key = item.key
            if key in self._store:
                items.append(state_pb2.BulkStateItem(
                    key=key,
                    data=self._store[key],
                    etag=self._etags.get(key, ""),
                ))
            else:
                items.append(state_pb2.BulkStateItem(
                    key=key,
                    error="key not found",
                ))

        return state_pb2.BulkGetResponse(items=items)

    def Set(self, request: state_pb2.SetRequest, context) -> state_pb2.SetResponse:
        """
        Store a single state value.
        """
        key = request.key
        logger.debug(f"Set: {key}")

        # Check ETag for optimistic concurrency
        if request.etag and request.etag != self._etags.get(key, ""):
            context.abort(grpc.StatusCode.ABORTED, "ETag mismatch")

        # Store the value
        self._store[key] = request.value
        self._etags[key] = self._generate_etag(request.value)

        return state_pb2.SetResponse()

    def BulkSet(self, request: state_pb2.BulkSetRequest, context) -> state_pb2.BulkSetResponse:
        """
        Store multiple state values (transactional if supported).
        """
        for item in request.items:
            self._store[item.key] = item.value
            self._etags[item.key] = self._generate_etag(item.value)

        return state_pb2.BulkSetResponse()

    def Delete(self, request: state_pb2.DeleteRequest, context) -> state_pb2.DeleteResponse:
        """
        Delete a single state value.
        """
        key = request.key
        logger.debug(f"Delete: {key}")

        # Check ETag for optimistic concurrency
        if request.etag and request.etag != self._etags.get(key, ""):
            context.abort(grpc.StatusCode.ABORTED, "ETag mismatch")

        self._store.pop(key, None)
        self._etags.pop(key, None)

        return state_pb2.DeleteResponse()

    def BulkDelete(self, request: state_pb2.BulkDeleteRequest, context) -> state_pb2.BulkDeleteResponse:
        """
        Delete multiple state values.
        """
        for item in request.items:
            self._store.pop(item.key, None)
            self._etags.pop(item.key, None)

        return state_pb2.BulkDeleteResponse()

    def Transact(self, request: state_pb2.TransactionalStateRequest, context) -> state_pb2.TransactionalStateResponse:
        """
        Execute transactional operations (set/delete).
        Only required if TRANSACTIONAL feature is declared.
        """
        for operation in request.operations:
            if operation.operationType == "upsert":
                self._store[operation.request.key] = operation.request.value
                self._etags[operation.request.key] = self._generate_etag(operation.request.value)
            elif operation.operationType == "delete":
                self._store.pop(operation.request.key, None)
                self._etags.pop(operation.request.key, None)

        return state_pb2.TransactionalStateResponse()

    def _generate_etag(self, data: bytes) -> str:
        """Generate ETag from data hash."""
        import hashlib
        return hashlib.md5(data).hexdigest()


def serve():
    """
    Start the gRPC server.

    DAPR connects via Unix Domain Socket at /tmp/dapr-components-sockets/<component-name>.sock
    """
    import os

    # Socket path - DAPR expects this format
    socket_path = os.environ.get(
        "DAPR_COMPONENT_SOCKET_PATH",
        "/tmp/dapr-components-sockets/my-state-store.sock"
    )

    # Clean up existing socket
    if os.path.exists(socket_path):
        os.remove(socket_path)

    # Ensure directory exists
    os.makedirs(os.path.dirname(socket_path), exist_ok=True)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    state_pb2_grpc.add_StateStoreServicer_to_server(CustomStateStore(), server)
    server.add_insecure_port(f"unix://{socket_path}")

    logger.info(f"Starting state store server on {socket_path}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
