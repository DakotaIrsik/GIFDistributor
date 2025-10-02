"""
Tests for observability module
"""
import pytest
import time
from observability import (
    StructuredLogger,
    MetricsCollector,
    Tracer,
    ObservabilityStack,
    LogLevel,
    MetricType
)


class TestStructuredLogger:
    """Test structured logging"""

    def test_basic_logging(self):
        """Test basic log creation"""
        logger = StructuredLogger("test-service")
        logger.info("Test message")

        logs = logger.get_logs()
        assert len(logs) == 1
        assert logs[0].message == "Test message"
        assert logs[0].level == "INFO"
        assert logs[0].service == "test-service"

    def test_log_levels(self):
        """Test different log levels"""
        logger = StructuredLogger("test-service", min_level=LogLevel.DEBUG)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        logs = logger.get_logs()
        assert len(logs) == 5
        assert logs[0].level == "DEBUG"
        assert logs[1].level == "INFO"
        assert logs[2].level == "WARNING"
        assert logs[3].level == "ERROR"
        assert logs[4].level == "CRITICAL"

    def test_log_filtering_by_level(self):
        """Test that logs below min level are filtered"""
        logger = StructuredLogger("test-service", min_level=LogLevel.WARNING)

        logger.debug("Debug")
        logger.info("Info")
        logger.warning("Warning")
        logger.error("Error")

        logs = logger.get_logs()
        assert len(logs) == 2
        assert all(log.level in ["WARNING", "ERROR"] for log in logs)

    def test_log_with_metadata(self):
        """Test logging with metadata"""
        logger = StructuredLogger("test-service")
        logger.info("User action", user_id="user123", action="upload")

        logs = logger.get_logs()
        assert logs[0].metadata["user_id"] == "user123"
        assert logs[0].metadata["action"] == "upload"

    def test_log_json_serialization(self):
        """Test log JSON serialization"""
        logger = StructuredLogger("test-service")
        logger.info("Test", key="value")

        logs = logger.get_logs()
        json_str = logs[0].to_json()
        assert "Test" in json_str
        assert "key" in json_str
        assert "value" in json_str

    def test_clear_logs(self):
        """Test clearing logs"""
        logger = StructuredLogger("test-service")
        logger.info("Message 1")
        logger.info("Message 2")

        assert len(logger.get_logs()) == 2

        logger.clear_logs()
        assert len(logger.get_logs()) == 0


class TestMetricsCollector:
    """Test metrics collection"""

    def test_counter_increment(self):
        """Test counter increments"""
        collector = MetricsCollector()
        collector.increment_counter("requests")
        collector.increment_counter("requests")
        collector.increment_counter("requests", value=3.0)

        assert collector.get_counter("requests") == 5.0

    def test_counter_with_tags(self):
        """Test counters with tags"""
        collector = MetricsCollector()
        collector.increment_counter("requests", tags={"endpoint": "/api/v1"})
        collector.increment_counter("requests", tags={"endpoint": "/api/v2"})

        assert collector.get_counter("requests", tags={"endpoint": "/api/v1"}) == 1.0
        assert collector.get_counter("requests", tags={"endpoint": "/api/v2"}) == 1.0

    def test_gauge_set(self):
        """Test gauge setting"""
        collector = MetricsCollector()
        collector.set_gauge("cpu_usage", 45.5)
        collector.set_gauge("cpu_usage", 50.2)

        assert collector.get_gauge("cpu_usage") == 50.2

    def test_gauge_with_tags(self):
        """Test gauges with tags"""
        collector = MetricsCollector()
        collector.set_gauge("memory_usage", 1024, tags={"host": "server1"})
        collector.set_gauge("memory_usage", 2048, tags={"host": "server2"})

        assert collector.get_gauge("memory_usage", tags={"host": "server1"}) == 1024
        assert collector.get_gauge("memory_usage", tags={"host": "server2"}) == 2048

    def test_histogram_recording(self):
        """Test histogram value recording"""
        collector = MetricsCollector()
        for value in [10, 20, 30, 40, 50]:
            collector.record_histogram("response_time", value)

        stats = collector.get_histogram_stats("response_time")
        assert stats["min"] == 10
        assert stats["max"] == 50
        assert stats["mean"] == 30
        assert stats["median"] == 30
        assert stats["count"] == 5

    def test_histogram_percentiles(self):
        """Test histogram percentile calculations"""
        collector = MetricsCollector()
        values = list(range(1, 101))  # 1 to 100
        for value in values:
            collector.record_histogram("latency", value)

        stats = collector.get_histogram_stats("latency")
        assert stats["p95"] == 95
        assert stats["p99"] == 99

    def test_timer_context_manager(self):
        """Test timing operations with context manager"""
        collector = MetricsCollector()

        with collector.time_operation("db_query"):
            time.sleep(0.01)  # 10ms

        stats = collector.get_histogram_stats("db_query")
        assert stats["count"] == 1
        assert stats["min"] >= 10  # At least 10ms

    def test_get_all_metrics(self):
        """Test getting all metrics"""
        collector = MetricsCollector()
        collector.increment_counter("requests")
        collector.set_gauge("cpu", 50.0)
        collector.record_histogram("latency", 100)

        metrics = collector.get_all_metrics()
        assert len(metrics) == 3
        assert any(m.name == "requests" for m in metrics)
        assert any(m.name == "cpu" for m in metrics)
        assert any(m.name == "latency" for m in metrics)

    def test_clear_metrics(self):
        """Test clearing metrics"""
        collector = MetricsCollector()
        collector.increment_counter("test")
        collector.set_gauge("test", 1.0)

        collector.clear_metrics()
        assert collector.get_counter("test") == 0.0
        assert collector.get_gauge("test") is None


class TestTracer:
    """Test distributed tracing"""

    def test_start_trace(self):
        """Test starting a new trace"""
        tracer = Tracer()
        span = tracer.start_trace("http_request")

        assert span.trace_id is not None
        assert span.span_id is not None
        assert span.parent_span_id is None
        assert span.operation == "http_request"
        assert span.status == "in_progress"

    def test_start_child_span(self):
        """Test starting a child span"""
        tracer = Tracer()
        root = tracer.start_trace("request")
        child = tracer.start_span("database_query", root)

        assert child.trace_id == root.trace_id
        assert child.parent_span_id == root.span_id
        assert child.span_id != root.span_id

    def test_finish_span(self):
        """Test finishing a span"""
        tracer = Tracer()
        span = tracer.start_trace("operation")

        time.sleep(0.01)
        tracer.finish_span(span)

        assert span.status == "success"
        assert span.end_time is not None
        assert span.duration_ms >= 10

    def test_finish_span_with_error(self):
        """Test finishing a span with error status"""
        tracer = Tracer()
        span = tracer.start_trace("failing_operation")
        tracer.finish_span(span, status="error")

        assert span.status == "error"

    def test_span_tags(self):
        """Test span tags"""
        tracer = Tracer()
        span = tracer.start_trace("request", tags={"http.method": "POST"})

        assert span.tags["http.method"] == "POST"

    def test_span_logs(self):
        """Test adding logs to spans"""
        tracer = Tracer()
        span = tracer.start_trace("operation")
        span.add_log("Started processing")
        span.add_log("Completed step 1", level="DEBUG")

        assert len(span.logs) == 2
        assert span.logs[0]["message"] == "Started processing"

    def test_get_trace(self):
        """Test retrieving a complete trace"""
        tracer = Tracer()
        root = tracer.start_trace("request")
        child1 = tracer.start_span("db_query", root)
        child2 = tracer.start_span("cache_check", root)

        trace = tracer.get_trace(root.trace_id)
        assert len(trace) == 3
        assert trace[0].operation == "request"

    def test_multiple_traces(self):
        """Test managing multiple independent traces"""
        tracer = Tracer()
        trace1 = tracer.start_trace("request1")
        trace2 = tracer.start_trace("request2")

        assert trace1.trace_id != trace2.trace_id

        all_traces = tracer.get_all_traces()
        assert len(all_traces) == 2

    def test_clear_traces(self):
        """Test clearing traces"""
        tracer = Tracer()
        tracer.start_trace("test")

        tracer.clear_traces()
        assert len(tracer.get_all_traces()) == 0


class TestObservabilityStack:
    """Test unified observability stack"""

    def test_initialization(self):
        """Test stack initialization"""
        obs = ObservabilityStack("my-service")

        assert obs.service_name == "my-service"
        assert obs.logger is not None
        assert obs.metrics is not None
        assert obs.tracer is not None

    def test_start_trace_creates_log_and_metric(self):
        """Test that starting a trace creates log and metric"""
        obs = ObservabilityStack("test-service")
        span = obs.start_trace("operation")

        # Should create a log entry
        logs = obs.logger.get_logs()
        assert len(logs) == 1
        assert "Starting trace" in logs[0].message

        # Should increment counter
        assert obs.metrics.get_counter("traces.started") == 1.0

    def test_finish_span_creates_log_and_metric(self):
        """Test that finishing a span creates log and histogram"""
        obs = ObservabilityStack("test-service")
        span = obs.start_trace("operation")
        time.sleep(0.01)
        obs.finish_span(span)

        # Should create another log entry
        logs = obs.logger.get_logs()
        assert len(logs) == 2
        assert "Finished span" in logs[1].message

        # Should record duration
        stats = obs.metrics.get_histogram_stats("span.duration")
        assert stats["count"] == 1

    def test_dashboard_data(self):
        """Test getting dashboard data"""
        obs = ObservabilityStack("test-service")

        obs.logger.info("Test message")
        obs.metrics.increment_counter("requests")
        obs.metrics.set_gauge("active_connections", 10)
        span = obs.start_trace("operation")
        obs.finish_span(span)

        dashboard = obs.get_dashboard_data()
        assert dashboard["service"] == "test-service"
        assert "logs" in dashboard
        assert "metrics" in dashboard
        assert "traces" in dashboard

    def test_integrated_workflow(self):
        """Test complete integrated workflow"""
        obs = ObservabilityStack("api-server")

        # Start a request trace
        request_span = obs.start_trace("http_request", method="GET", path="/api/users")

        # Log some events
        obs.logger.info("Received request", method="GET")

        # Record metrics
        obs.metrics.increment_counter("http.requests", tags={"method": "GET"})

        # Simulate child operations
        db_span = obs.tracer.start_span("db_query", request_span)
        time.sleep(0.01)
        obs.tracer.finish_span(db_span)

        cache_span = obs.tracer.start_span("cache_lookup", request_span)
        time.sleep(0.005)
        obs.tracer.finish_span(cache_span)

        # Complete request
        obs.finish_span(request_span)

        # Verify everything is tracked
        assert len(obs.logger.get_logs()) >= 2
        assert obs.metrics.get_counter("http.requests", tags={"method": "GET"}) == 1.0
        trace = obs.tracer.get_trace(request_span.trace_id)
        assert len(trace) == 3


class TestIntegration:
    """Test integration scenarios"""

    def test_trace_context_in_logs(self):
        """Test that trace context is automatically included in logs"""
        obs = ObservabilityStack("test-service")
        span = obs.start_trace("operation")

        # Log within trace context
        obs.logger.info("Processing request")

        logs = obs.logger.get_logs()
        # Find the processing log
        processing_log = [l for l in logs if "Processing request" in l.message][0]
        assert processing_log.trace_id == span.trace_id

    def test_performance_monitoring(self):
        """Test monitoring performance across multiple operations"""
        obs = ObservabilityStack("worker-service")

        # Simulate 100 operations with varying durations
        for i in range(100):
            span = obs.start_trace(f"job_{i}")
            time.sleep(0.001 * (i % 10))  # Variable sleep
            obs.finish_span(span)

        # Check metrics
        stats = obs.metrics.get_histogram_stats("span.duration")
        assert stats["count"] == 100
        assert stats["min"] < stats["max"]

    def test_error_tracking(self):
        """Test tracking errors through observability"""
        obs = ObservabilityStack("api-service")

        span = obs.start_trace("failing_request")
        try:
            # Simulate error
            raise ValueError("Something went wrong")
        except ValueError as e:
            obs.logger.error("Request failed", error=str(e))
            obs.finish_span(span, status="error")

        # Verify error is tracked
        logs = obs.logger.get_logs()
        error_logs = [l for l in logs if l.level == "ERROR"]
        assert len(error_logs) == 1
        assert span.status == "error"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_histogram_stats(self):
        """Test getting stats from empty histogram"""
        collector = MetricsCollector()
        stats = collector.get_histogram_stats("nonexistent")
        assert stats == {}

    def test_nonexistent_trace(self):
        """Test getting nonexistent trace"""
        tracer = Tracer()
        trace = tracer.get_trace("fake-trace-id")
        assert trace == []

    def test_logger_with_none_values(self):
        """Test logging with None metadata values"""
        logger = StructuredLogger("test")
        logger.info("Test", value=None)

        logs = logger.get_logs()
        assert logs[0].metadata["value"] is None

    def test_metrics_with_zero_value(self):
        """Test metrics with zero values"""
        collector = MetricsCollector()
        collector.increment_counter("zero_counter", value=0.0)
        collector.set_gauge("zero_gauge", 0.0)

        assert collector.get_counter("zero_counter") == 0.0
        assert collector.get_gauge("zero_gauge") == 0.0

    def test_span_finished_twice(self):
        """Test finishing a span multiple times"""
        tracer = Tracer()
        span = tracer.start_trace("operation")

        tracer.finish_span(span)
        first_duration = span.duration_ms

        time.sleep(0.01)
        tracer.finish_span(span)
        second_duration = span.duration_ms

        # Duration should be different (span was finished again)
        assert first_duration != second_duration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
