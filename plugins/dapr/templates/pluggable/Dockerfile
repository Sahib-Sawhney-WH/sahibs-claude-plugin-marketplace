# DAPR Pluggable Component Container
# ===================================
#
# Build a container for your pluggable component.
# The component exposes a Unix Domain Socket for DAPR communication.
#
# Build:
#   docker build -t my-pluggable-component:latest .
#
# Run locally (for testing):
#   docker run -v /tmp/dapr-components-sockets:/tmp/dapr-components-sockets \
#              -e DAPR_COMPONENT_SOCKET_PATH=/tmp/dapr-components-sockets/my-component.sock \
#              my-pluggable-component:latest

# ==================
# Python Component
# ==================
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy component code
COPY *.py .

# Generate proto stubs (if not pre-generated)
# RUN python -m grpc_tools.protoc \
#     -I./protos \
#     --python_out=. \
#     --grpc_python_out=. \
#     ./protos/dapr/proto/components/v1/*.proto

# Create socket directory
RUN mkdir -p /tmp/dapr-components-sockets

# Environment variables
ENV DAPR_COMPONENT_SOCKET_PATH=/tmp/dapr-components-sockets/my-component.sock
ENV PYTHONUNBUFFERED=1

# Run the component
CMD ["python", "state-store.py"]

# ==================
# Go Component (alternative)
# ==================
# FROM golang:1.21-alpine AS builder
#
# WORKDIR /app
# COPY go.mod go.sum ./
# RUN go mod download
#
# COPY . .
# RUN CGO_ENABLED=0 go build -o /component .
#
# FROM alpine:3.18
# RUN apk --no-cache add ca-certificates
# COPY --from=builder /component /component
# RUN mkdir -p /tmp/dapr-components-sockets
# ENV DAPR_COMPONENT_SOCKET_PATH=/tmp/dapr-components-sockets/my-component.sock
# CMD ["/component"]

# ==================
# Requirements.txt
# ==================
# Create a requirements.txt with:
#
# grpcio>=1.60.0
# grpcio-tools>=1.60.0
# protobuf>=4.25.0

# ==================
# Kubernetes Sidecar Pattern
# ==================
# In Kubernetes, deploy this container as a sidecar with your app.
# Share the socket directory via an emptyDir volume.
#
# See component.yaml for full Kubernetes deployment example.

# ==================
# Health Check
# ==================
# Add a health check endpoint if needed
# HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
#   CMD python -c "import os; exit(0 if os.path.exists('$DAPR_COMPONENT_SOCKET_PATH') else 1)"
