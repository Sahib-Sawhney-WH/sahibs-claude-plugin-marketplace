"""
DAPR Pluggable Binding Component
================================

Implement a custom input/output binding using gRPC protocol.
DAPR communicates with this component via Unix Domain Socket.

Requirements:
    pip install dapr-ext-grpc grpcio grpcio-tools

Usage:
    1. Implement the InputBinding and/or OutputBinding interfaces
    2. Build and run as a container or process
    3. Register with DAPR using component.yaml

Proto definitions: https://github.com/dapr/dapr/tree/master/dapr/proto
"""

import json
import logging
import time
import threading
from concurrent import futures
from typing import Any, Dict, Generator, List, Optional

import grpc

# Import generated proto stubs
from dapr.proto.components.v1 import bindings_pb2
from dapr.proto.components.v1 import bindings_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomInputBinding(bindings_pb2_grpc.InputBindingServicer):
    """
    Custom Input Binding Implementation.

    Input bindings trigger your application when external events occur.

    Methods:
    - Init: Initialize with metadata
    - Read: Stream events to DAPR (which forwards to your app)
    """

    def __init__(self):
        self._metadata: Dict[str, str] = {}
        self._running = True

    def Init(self, request: bindings_pb2.InputBindingInitRequest, context) -> bindings_pb2.InputBindingInitResponse:
        """
        Initialize the input binding with configuration.
        """
        logger.info("Initializing custom input binding")

        for item in request.metadata.properties:
            self._metadata[item.key] = item.value

        # Example: Set up your event source
        # poll_interval = int(self._metadata.get("pollInterval", "5"))
        # self._source = MyEventSource(poll_interval)

        return bindings_pb2.InputBindingInitResponse()

    def Read(self, request: bindings_pb2.ReadRequest, context) -> Generator[bindings_pb2.ReadResponse, None, None]:
        """
        Stream events to DAPR (server-streaming RPC).

        DAPR calls this method and your app receives events at:
        POST /{binding-name}

        Yield ReadResponse for each event.
        """
        logger.info("Starting input binding read stream")

        while context.is_active() and self._running:
            try:
                # Example: Poll your event source
                # Replace this with your actual event polling logic
                event = self._poll_for_event()

                if event:
                    yield bindings_pb2.ReadResponse(
                        data=json.dumps(event).encode("utf-8"),
                        metadata={
                            "source": "custom-binding",
                            "timestamp": str(int(time.time())),
                        },
                        content_type="application/json",
                    )
                else:
                    # No event, wait before polling again
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error reading event: {e}")
                time.sleep(5)  # Back off on error

    def _poll_for_event(self) -> Optional[Dict]:
        """
        Poll for events from your source.
        Replace with your actual implementation.
        """
        # Example: Simulated event every 10 seconds
        # In reality, poll a queue, watch a file, etc.
        return None


class CustomOutputBinding(bindings_pb2_grpc.OutputBindingServicer):
    """
    Custom Output Binding Implementation.

    Output bindings let your application invoke external systems.

    Methods:
    - Init: Initialize with metadata
    - Invoke: Handle binding invocations
    - ListOperations: Declare supported operations
    """

    def __init__(self):
        self._metadata: Dict[str, str] = {}

    def Init(self, request: bindings_pb2.OutputBindingInitRequest, context) -> bindings_pb2.OutputBindingInitResponse:
        """
        Initialize the output binding with configuration.
        """
        logger.info("Initializing custom output binding")

        for item in request.metadata.properties:
            self._metadata[item.key] = item.value

        # Example: Set up connection to external system
        # endpoint = self._metadata.get("endpoint")
        # self._client = MyExternalClient(endpoint)

        return bindings_pb2.OutputBindingInitResponse()

    def Invoke(self, request: bindings_pb2.InvokeRequest, context) -> bindings_pb2.InvokeResponse:
        """
        Handle a binding invocation.

        Your app calls:
        POST /v1.0/bindings/{binding-name}
        {
            "data": {...},
            "operation": "create",
            "metadata": {...}
        }
        """
        operation = request.operation
        data = request.data
        metadata = dict(request.metadata)

        logger.info(f"Invoke operation: {operation}")

        try:
            result = self._handle_operation(operation, data, metadata)

            return bindings_pb2.InvokeResponse(
                data=json.dumps(result).encode("utf-8") if result else b"",
                metadata={"status": "success"},
                content_type="application/json",
            )

        except ValueError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def ListOperations(self, request: bindings_pb2.ListOperationsRequest, context) -> bindings_pb2.ListOperationsResponse:
        """
        Declare which operations this binding supports.

        Common operations: create, get, delete, list
        """
        return bindings_pb2.ListOperationsResponse(
            operations=[
                bindings_pb2.BindingOperation(name="create"),
                bindings_pb2.BindingOperation(name="get"),
                bindings_pb2.BindingOperation(name="delete"),
                bindings_pb2.BindingOperation(name="list"),
            ]
        )

    def _handle_operation(self, operation: str, data: bytes, metadata: Dict[str, str]) -> Optional[Dict]:
        """
        Handle specific operations.
        Replace with your actual implementation.
        """
        payload = json.loads(data.decode("utf-8")) if data else {}

        if operation == "create":
            # Create resource in external system
            # result = self._client.create(payload)
            return {"id": "created-123", "status": "created"}

        elif operation == "get":
            # Get resource from external system
            resource_id = metadata.get("id")
            # result = self._client.get(resource_id)
            return {"id": resource_id, "data": "..."}

        elif operation == "delete":
            # Delete resource
            resource_id = metadata.get("id")
            # self._client.delete(resource_id)
            return {"id": resource_id, "status": "deleted"}

        elif operation == "list":
            # List resources
            # results = self._client.list()
            return {"items": [], "count": 0}

        else:
            raise ValueError(f"Unsupported operation: {operation}")


def serve():
    """
    Start the gRPC server for both input and output binding.
    """
    import os

    socket_path = os.environ.get(
        "DAPR_COMPONENT_SOCKET_PATH",
        "/tmp/dapr-components-sockets/my-binding.sock"
    )

    if os.path.exists(socket_path):
        os.remove(socket_path)

    os.makedirs(os.path.dirname(socket_path), exist_ok=True)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Register both input and output binding services
    bindings_pb2_grpc.add_InputBindingServicer_to_server(CustomInputBinding(), server)
    bindings_pb2_grpc.add_OutputBindingServicer_to_server(CustomOutputBinding(), server)

    server.add_insecure_port(f"unix://{socket_path}")

    logger.info(f"Starting binding server on {socket_path}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
