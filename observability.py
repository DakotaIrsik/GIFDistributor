"""
Observability module for logging, metrics, and tracing

Provides structured logging, metrics collection, and distributed tracing
for monitoring and debugging GIFDistributor services.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import contextvars

# Context variable for trace ID
_trace_context = contextvars.ContextVar("trace_context", default=None)


class LogLevel(Enum):
    """Standard log levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(Enum):
    """Types of metrics"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class LogEntry:
    """Structured log entry"""

    timestamp: str
    level: str
    message: str
    service: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self))


@dataclass
class Metric:
    """Metric data point"""

    name: str
    value: float
    metric_type: str
    timestamp: str
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Span:
    """Distributed tracing span"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "in_progress"  # in_progress, success, error
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, status: str = "success"):
        """Complete the span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def add_log(self, message: str, level: str = "INFO", **kwargs):
        """Add a log entry to this span"""
        self.logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "level": level,
                "message": message,
                **kwargs,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class StructuredLogger:
    """
    Structured JSON logger with trace context support

    Provides consistent structured logging across services with
    automatic trace ID injection and metadata support.
    """

    def __init__(self, service_name: str, min_level: LogLevel = LogLevel.INFO):
        """
        Initialize structured logger

        Args:
            service_name: Name of the service
            min_level: Minimum log level to emit
        """
        self.service_name = service_name
        self.min_level = min_level
        self._logs: List[LogEntry] = []

    def _should_log(self, level: LogLevel) -> bool:
        """Check if message at level should be logged"""
        levels = [
            LogLevel.DEBUG,
            LogLevel.INFO,
            LogLevel.WARNING,
            LogLevel.ERROR,
            LogLevel.CRITICAL,
        ]
        return levels.index(level) >= levels.index(self.min_level)

    def _log(self, level: LogLevel, message: str, **metadata):
        """Internal log method"""
        if not self._should_log(level):
            return

        trace_ctx = _trace_context.get()
        trace_id = trace_ctx.trace_id if trace_ctx else None
        span_id = trace_ctx.span_id if trace_ctx else None

        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            level=level.value,
            message=message,
            service=self.service_name,
            trace_id=trace_id,
            span_id=span_id,
            metadata=metadata,
        )
        self._logs.append(entry)

        # Also log to standard logging
        log_func = getattr(logging, level.value.lower())
        log_func(entry.to_json())

    def debug(self, message: str, **metadata):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **metadata)

    def info(self, message: str, **metadata):
        """Log info message"""
        self._log(LogLevel.INFO, message, **metadata)

    def warning(self, message: str, **metadata):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **metadata)

    def error(self, message: str, **metadata):
        """Log error message"""
        self._log(LogLevel.ERROR, message, **metadata)

    def critical(self, message: str, **metadata):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **metadata)

    def get_logs(self, trace_id: Optional[str] = None) -> List[LogEntry]:
        """
        Get log entries, optionally filtered by trace ID

        Args:
            trace_id: Optional trace ID to filter by

        Returns:
            List of log entries
        """
        if trace_id is None:
            return self._logs.copy()
        return [log for log in self._logs if log.trace_id == trace_id]

    def clear_logs(self):
        """Clear all stored logs"""
        self._logs.clear()


class MetricsCollector:
    """
    Metrics collector for counters, gauges, histograms, and timers

    Collects and aggregates metrics for monitoring service health
    and performance.
    """

    def __init__(self):
        """Initialize metrics collector"""
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._metrics: List[Metric] = []

    def increment_counter(
        self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None
    ):
        """
        Increment a counter metric

        Args:
            name: Counter name
            value: Amount to increment (default 1.0)
            tags: Optional tags for the metric
        """
        key = self._make_key(name, tags or {})
        self._counters[key] += value

        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER.value,
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            tags=tags or {},
        )
        self._metrics.append(metric)

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric to a specific value

        Args:
            name: Gauge name
            value: Current value
            tags: Optional tags for the metric
        """
        key = self._make_key(name, tags or {})
        self._gauges[key] = value

        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE.value,
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            tags=tags or {},
        )
        self._metrics.append(metric)

    def record_histogram(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a value in a histogram

        Args:
            name: Histogram name
            value: Value to record
            tags: Optional tags for the metric
        """
        key = self._make_key(name, tags or {})
        self._histograms[key].append(value)

        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM.value,
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            tags=tags or {},
        )
        self._metrics.append(metric)

    def time_operation(self, name: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing operations

        Args:
            name: Timer name
            tags: Optional tags for the metric

        Usage:
            with collector.time_operation("db_query"):
                # code to time
                pass
        """
        return Timer(self, name, tags or {})

    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value"""
        key = self._make_key(name, tags or {})
        return self._counters.get(key, 0.0)

    def get_gauge(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get current gauge value"""
        key = self._make_key(name, tags or {})
        return self._gauges.get(key)

    def get_histogram_stats(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """
        Get statistics for a histogram

        Returns:
            Dictionary with min, max, mean, median, p95, p99
        """
        key = self._make_key(name, tags or {})
        values = self._histograms.get(key, [])

        if not values:
            return {}

        sorted_values = sorted(values)
        n = len(sorted_values)

        p95_idx = max(0, int(n * 0.95) - 1)
        p99_idx = max(0, int(n * 0.99) - 1)

        return {
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "mean": sum(sorted_values) / n,
            "median": sorted_values[n // 2],
            "p95": sorted_values[p95_idx],
            "p99": sorted_values[p99_idx],
            "count": n,
        }

    def get_all_metrics(self) -> List[Metric]:
        """Get all recorded metrics"""
        return self._metrics.copy()

    def clear_metrics(self):
        """Clear all metrics"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._metrics.clear()

    def _make_key(self, name: str, tags: Dict[str, str]) -> str:
        """Create a unique key from metric name and tags"""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"


class Timer:
    """Context manager for timing operations"""

    def __init__(self, collector: MetricsCollector, name: str, tags: Dict[str, str]):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.collector.record_histogram(self.name, duration_ms, self.tags)


class Tracer:
    """
    Distributed tracing implementation

    Creates and manages spans for distributed tracing across services.
    """

    def __init__(self):
        """Initialize tracer"""
        self._spans: Dict[str, List[Span]] = defaultdict(list)
        self._active_spans: Dict[str, Span] = {}
        self._span_counter = 0

    def start_trace(
        self, operation: str, tags: Optional[Dict[str, str]] = None
    ) -> Span:
        """
        Start a new trace (root span)

        Args:
            operation: Name of the operation
            tags: Optional tags for the span

        Returns:
            New root span
        """
        trace_id = self._generate_trace_id()
        span_id = self._generate_span_id()

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation=operation,
            start_time=time.time(),
            tags=tags or {},
        )

        self._spans[trace_id].append(span)
        self._active_spans[span_id] = span

        # Set trace context
        _trace_context.set(span)

        return span

    def start_span(
        self, operation: str, parent_span: Span, tags: Optional[Dict[str, str]] = None
    ) -> Span:
        """
        Start a child span

        Args:
            operation: Name of the operation
            parent_span: Parent span
            tags: Optional tags for the span

        Returns:
            New child span
        """
        span_id = self._generate_span_id()

        span = Span(
            trace_id=parent_span.trace_id,
            span_id=span_id,
            parent_span_id=parent_span.span_id,
            operation=operation,
            start_time=time.time(),
            tags=tags or {},
        )

        self._spans[parent_span.trace_id].append(span)
        self._active_spans[span_id] = span

        # Update trace context
        _trace_context.set(span)

        return span

    def finish_span(self, span: Span, status: str = "success"):
        """
        Finish a span

        Args:
            span: Span to finish
            status: Status (success, error)
        """
        span.finish(status)
        if span.span_id in self._active_spans:
            del self._active_spans[span.span_id]

    def get_trace(self, trace_id: str) -> List[Span]:
        """
        Get all spans for a trace

        Args:
            trace_id: Trace ID

        Returns:
            List of spans in the trace
        """
        return self._spans.get(trace_id, []).copy()

    def get_all_traces(self) -> Dict[str, List[Span]]:
        """Get all traces"""
        return {k: v.copy() for k, v in self._spans.items()}

    def clear_traces(self):
        """Clear all traces"""
        self._spans.clear()
        self._active_spans.clear()

    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID"""
        import uuid

        return uuid.uuid4().hex

    def _generate_span_id(self) -> str:
        """Generate a unique span ID"""
        self._span_counter += 1
        return f"span_{self._span_counter:08x}"


class ObservabilityStack:
    """
    Unified observability stack combining logs, metrics, and traces

    Provides a single interface for all observability needs.
    """

    def __init__(self, service_name: str, min_log_level: LogLevel = LogLevel.INFO):
        """
        Initialize observability stack

        Args:
            service_name: Name of the service
            min_log_level: Minimum log level
        """
        self.service_name = service_name
        self.logger = StructuredLogger(service_name, min_log_level)
        self.metrics = MetricsCollector()
        self.tracer = Tracer()

    def start_trace(self, operation: str, **tags) -> Span:
        """Start a new trace"""
        span = self.tracer.start_trace(operation, tags)
        self.logger.info(f"Starting trace: {operation}", trace_id=span.trace_id)
        self.metrics.increment_counter("traces.started")
        return span

    def finish_span(self, span: Span, status: str = "success"):
        """Finish a span"""
        self.tracer.finish_span(span, status)
        self.logger.info(
            f"Finished span: {span.operation}",
            trace_id=span.trace_id,
            duration_ms=span.duration_ms,
            status=status,
        )
        self.metrics.record_histogram("span.duration", span.duration_ms)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get aggregated data for dashboard

        Returns:
            Dictionary with logs, metrics, and trace summaries
        """
        return {
            "service": self.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "logs": {
                "total": len(self.logger.get_logs()),
                "by_level": self._count_logs_by_level(),
            },
            "metrics": {
                "counters": dict(self.metrics._counters),
                "gauges": dict(self.metrics._gauges),
                "histograms": {
                    name: self.metrics.get_histogram_stats(
                        name.split("{")[0], self._parse_tags(name)
                    )
                    for name in self.metrics._histograms.keys()
                },
            },
            "traces": {
                "total": len(self.tracer._spans),
                "active": len(self.tracer._active_spans),
            },
        }

    def _count_logs_by_level(self) -> Dict[str, int]:
        """Count logs by level"""
        counts = defaultdict(int)
        for log in self.logger.get_logs():
            counts[log.level] += 1
        return dict(counts)

    def _parse_tags(self, key: str) -> Dict[str, str]:
        """Parse tags from metric key"""
        if "{" not in key:
            return {}
        tag_str = key.split("{")[1].rstrip("}")
        return dict(pair.split("=") for pair in tag_str.split(",") if pair)
