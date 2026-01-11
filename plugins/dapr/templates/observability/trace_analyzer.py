"""
DAPR Distributed Trace Analyzer

Analyzes distributed traces from Zipkin/Jaeger/Azure Monitor to identify:
- Slow spans and bottlenecks
- Error patterns and failure chains
- Critical path analysis
- Service dependency mapping
- Performance recommendations

Usage:
    from observability.trace_analyzer import TraceAnalyzer

    analyzer = TraceAnalyzer()
    results = analyzer.analyze_traces(traces)
    recommendations = analyzer.get_recommendations(results)
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from statistics import mean, median, stdev

logger = logging.getLogger(__name__)


class TraceFormat(Enum):
    """Supported trace formats."""
    ZIPKIN = "zipkin"
    JAEGER = "jaeger"
    OTLP = "otlp"
    AZURE_MONITOR = "azure_monitor"


@dataclass
class Span:
    """Represents a single span in a trace."""
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    duration_ms: float
    status: str  # "OK", "ERROR", "UNSET"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    children: List["Span"] = field(default_factory=list)

    @property
    def is_error(self) -> bool:
        return self.status == "ERROR" or self.tags.get("error") == True

    @property
    def is_dapr_sidecar(self) -> bool:
        return "dapr" in self.service_name.lower() or self.tags.get("dapr.api", False)

    @property
    def component_type(self) -> Optional[str]:
        """Extract DAPR component type if available."""
        return self.tags.get("dapr.component.type")


@dataclass
class TraceAnalysisResult:
    """Results from trace analysis."""
    trace_id: str
    total_duration_ms: float
    span_count: int
    service_count: int
    error_count: int
    critical_path: List[Span]
    slow_spans: List[Span]
    error_spans: List[Span]
    dapr_overhead_ms: float
    service_breakdown: Dict[str, float]  # service -> total time
    bottlenecks: List[Dict[str, Any]]


@dataclass
class AggregateAnalysis:
    """Aggregate analysis across multiple traces."""
    total_traces: int
    error_rate: float
    avg_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    slow_operations: List[Dict[str, Any]]
    error_patterns: List[Dict[str, Any]]
    service_latency: Dict[str, Dict[str, float]]
    recommendations: List[str]


class TraceParser:
    """Parses trace data from various formats into Span objects."""

    @staticmethod
    def parse_zipkin(data: List[Dict]) -> List[Span]:
        """Parse Zipkin trace format."""
        spans = []
        for item in data:
            try:
                start_time = datetime.fromtimestamp(item["timestamp"] / 1_000_000)
                duration_ms = item.get("duration", 0) / 1000

                status = "OK"
                tags = item.get("tags", {})
                if tags.get("error"):
                    status = "ERROR"
                if tags.get("otel.status_code") == "ERROR":
                    status = "ERROR"

                span = Span(
                    trace_id=item["traceId"],
                    span_id=item["id"],
                    parent_id=item.get("parentId"),
                    operation_name=item.get("name", "unknown"),
                    service_name=item.get("localEndpoint", {}).get("serviceName", "unknown"),
                    start_time=start_time,
                    duration_ms=duration_ms,
                    status=status,
                    tags=tags,
                    logs=item.get("annotations", [])
                )
                spans.append(span)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse Zipkin span: {e}")

        return spans

    @staticmethod
    def parse_jaeger(data: Dict) -> List[Span]:
        """Parse Jaeger trace format."""
        spans = []
        traces = data.get("data", [])

        for trace_data in traces:
            processes = trace_data.get("processes", {})

            for span_data in trace_data.get("spans", []):
                try:
                    process = processes.get(span_data.get("processID", ""), {})
                    service_name = process.get("serviceName", "unknown")

                    start_time = datetime.fromtimestamp(span_data["startTime"] / 1_000_000)
                    duration_ms = span_data.get("duration", 0) / 1000

                    # Convert tags to dict
                    tags = {}
                    for tag in span_data.get("tags", []):
                        tags[tag["key"]] = tag["value"]

                    status = "OK"
                    if tags.get("error") or tags.get("otel.status_code") == "ERROR":
                        status = "ERROR"

                    # Get parent ID from references
                    parent_id = None
                    for ref in span_data.get("references", []):
                        if ref.get("refType") == "CHILD_OF":
                            parent_id = ref.get("spanID")
                            break

                    span = Span(
                        trace_id=span_data["traceID"],
                        span_id=span_data["spanID"],
                        parent_id=parent_id,
                        operation_name=span_data.get("operationName", "unknown"),
                        service_name=service_name,
                        start_time=start_time,
                        duration_ms=duration_ms,
                        status=status,
                        tags=tags,
                        logs=span_data.get("logs", [])
                    )
                    spans.append(span)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse Jaeger span: {e}")

        return spans

    @staticmethod
    def parse_azure_monitor(data: List[Dict]) -> List[Span]:
        """Parse Azure Monitor Application Insights format."""
        spans = []

        for item in data:
            try:
                start_time = datetime.fromisoformat(
                    item["timestamp"].replace("Z", "+00:00")
                )
                duration_ms = item.get("duration", 0)

                # Azure Monitor uses different status codes
                status = "OK"
                if item.get("success") == False:
                    status = "ERROR"
                if item.get("resultCode", "").startswith("5"):
                    status = "ERROR"

                tags = item.get("customDimensions", {})
                tags.update({
                    "http.status_code": item.get("resultCode"),
                    "http.url": item.get("url"),
                    "http.method": item.get("name", "").split()[0] if " " in item.get("name", "") else None
                })

                span = Span(
                    trace_id=item.get("operation_Id", ""),
                    span_id=item.get("id", ""),
                    parent_id=item.get("operation_ParentId"),
                    operation_name=item.get("name", "unknown"),
                    service_name=item.get("cloud_RoleName", "unknown"),
                    start_time=start_time,
                    duration_ms=duration_ms,
                    status=status,
                    tags=tags
                )
                spans.append(span)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse Azure Monitor span: {e}")

        return spans


class TraceAnalyzer:
    """Analyzes distributed traces for performance and error patterns."""

    def __init__(
        self,
        slow_threshold_ms: float = 1000.0,
        dapr_overhead_threshold_ms: float = 50.0
    ):
        self.slow_threshold_ms = slow_threshold_ms
        self.dapr_overhead_threshold_ms = dapr_overhead_threshold_ms
        self.parser = TraceParser()

    def parse_traces(
        self,
        data: Any,
        format: TraceFormat = TraceFormat.ZIPKIN
    ) -> List[Span]:
        """Parse trace data into Span objects."""
        if format == TraceFormat.ZIPKIN:
            return self.parser.parse_zipkin(data)
        elif format == TraceFormat.JAEGER:
            return self.parser.parse_jaeger(data)
        elif format == TraceFormat.AZURE_MONITOR:
            return self.parser.parse_azure_monitor(data)
        else:
            raise ValueError(f"Unsupported trace format: {format}")

    def analyze_trace(self, spans: List[Span]) -> TraceAnalysisResult:
        """Analyze a single trace (list of spans with same trace_id)."""
        if not spans:
            raise ValueError("No spans to analyze")

        trace_id = spans[0].trace_id

        # Build span tree
        span_map = {s.span_id: s for s in spans}
        root_spans = []

        for span in spans:
            if span.parent_id and span.parent_id in span_map:
                span_map[span.parent_id].children.append(span)
            else:
                root_spans.append(span)

        # Calculate metrics
        total_duration = max(s.duration_ms for s in spans)
        error_spans = [s for s in spans if s.is_error]
        slow_spans = [s for s in spans if s.duration_ms > self.slow_threshold_ms]

        # Calculate DAPR overhead
        dapr_spans = [s for s in spans if s.is_dapr_sidecar]
        dapr_overhead = sum(s.duration_ms for s in dapr_spans)

        # Service breakdown
        service_breakdown = defaultdict(float)
        for span in spans:
            service_breakdown[span.service_name] += span.duration_ms

        # Find critical path (longest path through trace)
        critical_path = self._find_critical_path(root_spans)

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(spans, total_duration)

        return TraceAnalysisResult(
            trace_id=trace_id,
            total_duration_ms=total_duration,
            span_count=len(spans),
            service_count=len(set(s.service_name for s in spans)),
            error_count=len(error_spans),
            critical_path=critical_path,
            slow_spans=sorted(slow_spans, key=lambda s: -s.duration_ms),
            error_spans=error_spans,
            dapr_overhead_ms=dapr_overhead,
            service_breakdown=dict(service_breakdown),
            bottlenecks=bottlenecks
        )

    def analyze_aggregate(
        self,
        traces: List[List[Span]]
    ) -> AggregateAnalysis:
        """Analyze multiple traces for patterns."""
        results = [self.analyze_trace(t) for t in traces if t]

        if not results:
            raise ValueError("No traces to analyze")

        durations = [r.total_duration_ms for r in results]
        error_traces = sum(1 for r in results if r.error_count > 0)

        # Calculate percentiles
        sorted_durations = sorted(durations)
        p50 = self._percentile(sorted_durations, 50)
        p95 = self._percentile(sorted_durations, 95)
        p99 = self._percentile(sorted_durations, 99)

        # Aggregate slow operations
        operation_times = defaultdict(list)
        for result in results:
            for span in result.slow_spans:
                key = f"{span.service_name}/{span.operation_name}"
                operation_times[key].append(span.duration_ms)

        slow_operations = [
            {
                "operation": op,
                "count": len(times),
                "avg_ms": mean(times),
                "max_ms": max(times)
            }
            for op, times in operation_times.items()
        ]
        slow_operations.sort(key=lambda x: -x["avg_ms"])

        # Aggregate error patterns
        error_patterns = defaultdict(int)
        for result in results:
            for span in result.error_spans:
                key = f"{span.service_name}/{span.operation_name}"
                error_patterns[key] += 1

        error_list = [
            {"operation": op, "count": count}
            for op, count in error_patterns.items()
        ]
        error_list.sort(key=lambda x: -x["count"])

        # Service latency breakdown
        service_latency = defaultdict(list)
        for result in results:
            for service, time in result.service_breakdown.items():
                service_latency[service].append(time)

        service_latency_stats = {
            service: {
                "avg_ms": mean(times),
                "p95_ms": self._percentile(sorted(times), 95),
                "max_ms": max(times)
            }
            for service, times in service_latency.items()
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(
            results, slow_operations, error_list
        )

        return AggregateAnalysis(
            total_traces=len(results),
            error_rate=error_traces / len(results),
            avg_duration_ms=mean(durations),
            p50_duration_ms=p50,
            p95_duration_ms=p95,
            p99_duration_ms=p99,
            slow_operations=slow_operations[:10],
            error_patterns=error_list[:10],
            service_latency=service_latency_stats,
            recommendations=recommendations
        )

    def _find_critical_path(self, root_spans: List[Span]) -> List[Span]:
        """Find the critical path through the trace tree."""
        if not root_spans:
            return []

        def find_longest_path(span: Span) -> Tuple[float, List[Span]]:
            if not span.children:
                return span.duration_ms, [span]

            child_paths = [find_longest_path(child) for child in span.children]
            longest = max(child_paths, key=lambda x: x[0])
            return span.duration_ms + longest[0], [span] + longest[1]

        all_paths = [find_longest_path(root) for root in root_spans]
        _, longest_path = max(all_paths, key=lambda x: x[0])
        return longest_path

    def _identify_bottlenecks(
        self,
        spans: List[Span],
        total_duration: float
    ) -> List[Dict[str, Any]]:
        """Identify bottleneck spans that consume significant trace time."""
        bottlenecks = []
        threshold = total_duration * 0.3  # Spans taking >30% of total time

        for span in spans:
            if span.duration_ms > threshold:
                bottlenecks.append({
                    "span_id": span.span_id,
                    "operation": span.operation_name,
                    "service": span.service_name,
                    "duration_ms": span.duration_ms,
                    "percentage": (span.duration_ms / total_duration) * 100,
                    "is_dapr": span.is_dapr_sidecar
                })

        return sorted(bottlenecks, key=lambda x: -x["duration_ms"])

    def _percentile(self, sorted_data: List[float], p: int) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)

    def _generate_recommendations(
        self,
        results: List[TraceAnalysisResult],
        slow_ops: List[Dict],
        errors: List[Dict]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Check DAPR overhead
        avg_dapr_overhead = mean(r.dapr_overhead_ms for r in results)
        if avg_dapr_overhead > self.dapr_overhead_threshold_ms:
            recommendations.append(
                f"High DAPR sidecar overhead ({avg_dapr_overhead:.1f}ms avg). "
                "Consider: optimizing component configuration, reducing serialization, "
                "or using HTTP instead of gRPC for smaller payloads."
            )

        # Check slow operations
        if slow_ops:
            top_slow = slow_ops[0]
            recommendations.append(
                f"Slowest operation: {top_slow['operation']} ({top_slow['avg_ms']:.1f}ms avg). "
                "Consider: adding caching, optimizing queries, or async processing."
            )

        # Check error patterns
        if errors:
            top_error = errors[0]
            recommendations.append(
                f"Most failing operation: {top_error['operation']} ({top_error['count']} failures). "
                "Review error logs and add retry policies or circuit breakers."
            )

        # Check for fan-out patterns
        high_span_traces = [r for r in results if r.span_count > 50]
        if len(high_span_traces) > len(results) * 0.5:
            recommendations.append(
                "High span count detected (>50 spans per trace). "
                "Consider: batching requests, reducing service calls, or using async patterns."
            )

        # Check error rate
        error_rate = sum(1 for r in results if r.error_count > 0) / len(results)
        if error_rate > 0.05:
            recommendations.append(
                f"High error rate ({error_rate*100:.1f}%). "
                "Implement proper error handling and add resiliency policies."
            )

        return recommendations


def analyze_trace_file(
    file_path: str,
    format: TraceFormat = TraceFormat.ZIPKIN,
    output_file: Optional[str] = None
) -> AggregateAnalysis:
    """
    Analyze traces from a JSON file.

    Args:
        file_path: Path to trace JSON file
        format: Trace format
        output_file: Optional file to write results

    Returns:
        AggregateAnalysis results
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    analyzer = TraceAnalyzer()

    # Parse and group by trace_id
    if format == TraceFormat.JAEGER:
        # Jaeger format has traces pre-grouped
        all_spans = analyzer.parse_traces(data, format)
    else:
        all_spans = analyzer.parse_traces(data, format)

    # Group spans by trace_id
    traces_by_id = defaultdict(list)
    for span in all_spans:
        traces_by_id[span.trace_id].append(span)

    traces = list(traces_by_id.values())

    # Analyze
    results = analyzer.analyze_aggregate(traces)

    if output_file:
        with open(output_file, 'w') as f:
            json.dump({
                "total_traces": results.total_traces,
                "error_rate": results.error_rate,
                "avg_duration_ms": results.avg_duration_ms,
                "p50_duration_ms": results.p50_duration_ms,
                "p95_duration_ms": results.p95_duration_ms,
                "p99_duration_ms": results.p99_duration_ms,
                "slow_operations": results.slow_operations,
                "error_patterns": results.error_patterns,
                "recommendations": results.recommendations
            }, f, indent=2)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze DAPR distributed traces")
    parser.add_argument("file", help="Trace JSON file")
    parser.add_argument(
        "--format", "-f",
        choices=["zipkin", "jaeger", "azure"],
        default="zipkin",
        help="Trace format"
    )
    parser.add_argument("--output", "-o", help="Output file for results")

    args = parser.parse_args()

    format_map = {
        "zipkin": TraceFormat.ZIPKIN,
        "jaeger": TraceFormat.JAEGER,
        "azure": TraceFormat.AZURE_MONITOR
    }

    results = analyze_trace_file(
        args.file,
        format_map[args.format],
        args.output
    )

    print(f"\nTrace Analysis Results")
    print(f"======================")
    print(f"Total traces: {results.total_traces}")
    print(f"Error rate: {results.error_rate*100:.2f}%")
    print(f"Average duration: {results.avg_duration_ms:.2f}ms")
    print(f"P50: {results.p50_duration_ms:.2f}ms")
    print(f"P95: {results.p95_duration_ms:.2f}ms")
    print(f"P99: {results.p99_duration_ms:.2f}ms")

    if results.recommendations:
        print(f"\nRecommendations:")
        for rec in results.recommendations:
            print(f"  - {rec}")
