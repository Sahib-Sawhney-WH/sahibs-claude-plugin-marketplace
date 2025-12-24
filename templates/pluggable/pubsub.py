"""
DAPR Pluggable Pub/Sub Component
================================

Implement a custom pub/sub broker using gRPC protocol.
DAPR communicates with this component via Unix Domain Socket.

Requirements:
    pip install dapr-ext-grpc grpcio grpcio-tools

Usage:
    1. Implement the PubSub interface methods
    2. Build and run as a container or process
    3. Register with DAPR using component.yaml

Proto definitions: https://github.com/dapr/dapr/tree/master/dapr/proto
"""

import asyncio
import json
import logging
import queue
import threading
from concurrent import futures
from typing import Any, Callable, Dict, List, Optional, Set

import grpc

# Import generated proto stubs
from dapr.proto.components.v1 import pubsub_pb2
from dapr.proto.components.v1 import pubsub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomPubSub(pubsub_pb2_grpc.PubSubServicer):
    """
    Custom Pub/Sub Implementation.

    Implement these methods to create your own pub/sub broker:
    - Init: Initialize the component with metadata
    - Features: Declare supported features
    - Publish: Publish a message to a topic
    - BulkPublish: Publish multiple messages
    - PullMessages: Stream messages to DAPR (for pull-based)
    """

    def __init__(self):
        self._metadata: Dict[str, str] = {}
        # In-memory message queues per topic (replace with real broker)
        self._topics: Dict[str, queue.Queue] = {}
        self._subscribers: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def Init(self, request: pubsub_pb2.PubSubInitRequest, context) -> pubsub_pb2.PubSubInitResponse:
        """
        Initialize the pub/sub component with configuration metadata.
        """
        logger.info("Initializing custom pub/sub")

        for item in request.metadata.properties:
            self._metadata[item.key] = item.value

        # Example: Connect to your message broker
        # broker_url = self._metadata.get("brokerUrl")
        # self._client = MyBrokerClient(broker_url)

        return pubsub_pb2.PubSubInitResponse()

    def Features(self, request: pubsub_pb2.FeaturesRequest, context) -> pubsub_pb2.FeaturesResponse:
        """
        Declare which features this pub/sub supports.

        Features:
        - SUBSCRIBE_WILDCARDS: Support topic wildcards (*, #)
        - MESSAGE_TTL: Time-to-live for messages
        - RAW_PAYLOAD: Non-CloudEvents format
        - BULK_PUBLISH: Batch publishing
        - BULK_SUBSCRIBE: Batch subscriptions
        """
        return pubsub_pb2.FeaturesResponse(
            features=[
                "BULK_PUBLISH",
                # "SUBSCRIBE_WILDCARDS",
                # "MESSAGE_TTL",
            ]
        )

    def Publish(self, request: pubsub_pb2.PublishRequest, context) -> pubsub_pb2.PublishResponse:
        """
        Publish a single message to a topic.
        """
        topic = request.topic
        data = request.data

        logger.debug(f"Publishing to topic: {topic}")

        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = queue.Queue()

            message = {
                "id": request.metadata.get("id", self._generate_id()),
                "data": data.decode("utf-8") if data else "",
                "topic": topic,
                "metadata": dict(request.metadata),
            }
            self._topics[topic].put(message)

        return pubsub_pb2.PublishResponse()

    def BulkPublish(self, request: pubsub_pb2.BulkPublishRequest, context) -> pubsub_pb2.BulkPublishResponse:
        """
        Publish multiple messages to a topic.
        """
        topic = request.topic
        failed_entries = []

        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = queue.Queue()

            for entry in request.entries:
                try:
                    message = {
                        "id": entry.entry_id,
                        "data": entry.event.decode("utf-8") if entry.event else "",
                        "topic": topic,
                        "metadata": dict(entry.metadata),
                    }
                    self._topics[topic].put(message)
                except Exception as e:
                    failed_entries.append(pubsub_pb2.BulkPublishResponseFailedEntry(
                        entry_id=entry.entry_id,
                        error=str(e),
                    ))

        return pubsub_pb2.BulkPublishResponse(failed_entries=failed_entries)

    def PullMessages(self, request: pubsub_pb2.PullMessagesRequest, context):
        """
        Stream messages to DAPR (pull-based subscription).

        This is a server-streaming RPC. DAPR calls this to receive messages.
        Yield PullMessagesResponse for each message.
        """
        topic = request.topic.topic
        logger.info(f"Starting pull subscription for topic: {topic}")

        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = queue.Queue()

        while context.is_active():
            try:
                # Wait for message with timeout
                message = self._topics[topic].get(timeout=1.0)

                yield pubsub_pb2.PullMessagesResponse(
                    data=message["data"].encode("utf-8"),
                    topic_name=topic,
                    metadata=message.get("metadata", {}),
                    content_type="application/json",
                )

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error pulling messages: {e}")
                break

    def AckMessage(self, request: pubsub_pb2.AckMessageRequest, context) -> pubsub_pb2.AckMessageResponse:
        """
        Acknowledge message receipt (for at-least-once delivery).
        """
        message_id = request.message_id
        logger.debug(f"Ack message: {message_id}")

        # Mark message as processed in your broker
        # self._broker.ack(message_id)

        return pubsub_pb2.AckMessageResponse()

    def _generate_id(self) -> str:
        """Generate unique message ID."""
        import uuid
        return str(uuid.uuid4())


def serve():
    """
    Start the gRPC server.
    """
    import os

    socket_path = os.environ.get(
        "DAPR_COMPONENT_SOCKET_PATH",
        "/tmp/dapr-components-sockets/my-pubsub.sock"
    )

    if os.path.exists(socket_path):
        os.remove(socket_path)

    os.makedirs(os.path.dirname(socket_path), exist_ok=True)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pubsub_pb2_grpc.add_PubSubServicer_to_server(CustomPubSub(), server)
    server.add_insecure_port(f"unix://{socket_path}")

    logger.info(f"Starting pub/sub server on {socket_path}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
