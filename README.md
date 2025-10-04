# GIFDistributor

A system for distributing and sharing GIF assets with short links and canonical URLs.

## Features

- **Share Links**: Generate short, shareable links for GIF assets (`/s/{short_code}`)
- **Canonical URLs**: Persistent asset URLs (`/a/{asset_id}`)
- **CDN Support**: Cache headers, HTTP Range requests, and signed URLs for secure delivery
- **Analytics Tracking**: Track views, plays, clicks, and CTR across platforms
- **Platform Metrics**: Break down engagement by platform (Slack, Discord, Teams, Twitter, etc.)
- **Deduplication**: Hash-based asset ID generation to avoid duplicate uploads
- **Metadata Support**: Open Graph tags for social media sharing
- **Rate Limiting**: Token bucket, fixed window, and sliding window strategies with per-IP/user limits
- **Observability**: Structured logging, metrics collection, and distributed tracing for monitoring
- **AI Safety Scanning**: OpenAI-powered content moderation with text and vision analysis for NSFW/unsafe content detection
- **Content Moderation**: SFW-only enforcement with automated scanning, audit trail, and manual review workflow

## Installation

```bash
pip install -r requirements.txt

# For AI safety scanning (optional):
pip install openai pillow
```

## Usage

### Basic Example

```python
from sharelinks import ShareLinkGenerator, create_asset_hash

# Initialize the generator
generator = ShareLinkGenerator(base_url="https://gifdist.io")

# Create a share link for an asset
link_info = generator.create_share_link(
    asset_id="abc123def456",
    title="Funny Cat GIF",
    tags=["cat", "funny", "pets"]
)

print(f"Short URL: {link_info['short_url']}")
print(f"Canonical URL: {link_info['canonical_url']}")
```

### Hash-Based Asset IDs

```python
# Generate hash-based ID for deduplication
file_hash = create_asset_hash("path/to/gif.gif")
asset_id = generator.generate_hash_based_id(file_hash)
```

### Resolving Short Links

```python
# Resolve a short code to get asset information
asset_info = generator.resolve_short_link("Ab12Cd34")
if asset_info:
    print(f"Asset ID: {asset_info['asset_id']}")
    print(f"Clicks: {asset_info['clicks']}")
```

### Integration: Share Links + Analytics

```python
from sharelinks import ShareLinkGenerator
from analytics import AnalyticsTracker, EventType, Platform

# Initialize both modules
generator = ShareLinkGenerator(base_url="https://gifdist.io")
tracker = AnalyticsTracker()

# Create a share link
link_info = generator.create_share_link(
    asset_id="abc123def456",
    title="Funny Cat GIF"
)

# Track analytics for the share link
tracker.track_event(
    asset_id="abc123def456",
    event_type=EventType.VIEW,
    platform=Platform.SLACK,
    short_code=link_info['short_code']
)

# Get metrics for the short link
short_link_metrics = tracker.get_short_link_metrics(link_info['short_code'])
print(f"Views: {short_link_metrics['views']}")
```

### Integration: Full Stack with Observability

```python
from sharelinks import ShareLinkGenerator
from analytics import AnalyticsTracker, EventType, Platform
from cdn import CDNHelper, CachePolicy
from observability import ObservabilityStack, LogLevel

# Initialize all modules with observability
obs = ObservabilityStack(service_name="gif-distributor", min_log_level=LogLevel.INFO)
generator = ShareLinkGenerator(base_url="https://gifdist.io")
tracker = AnalyticsTracker()
cdn = CDNHelper(secret_key="your-secret-key")

# Start trace for the complete operation
span = obs.start_trace("create_and_share_asset", asset_type="gif")

try:
    # Create share link with logging
    obs.logger.info("Creating share link", asset_id="abc123")
    link_info = generator.create_share_link(
        asset_id="abc123def456",
        title="Funny Cat GIF",
        tags=["cat", "funny"]
    )
    obs.metrics.increment_counter("sharelinks.created", tags={"status": "success"})

    # Track initial view with timing
    with obs.metrics.time_operation("analytics.track_event"):
        tracker.track_event(
            asset_id="abc123def456",
            event_type=EventType.VIEW,
            platform=Platform.SLACK,
            short_code=link_info['short_code']
        )

    # Create signed CDN URL
    signed_url = cdn.create_signed_asset_url(
        asset_url=link_info['canonical_url'],
        expiration_seconds=3600
    )
    obs.logger.info("Generated signed CDN URL", expires_in=3600)

    # Finish successfully
    obs.finish_span(span, status="success")

    # Get comprehensive metrics
    dashboard = obs.get_dashboard_data()
    print(f"Operation completed - Logs: {dashboard['logs']['total']}, "
          f"Active traces: {dashboard['traces']['active']}")

except Exception as e:
    obs.logger.error("Operation failed", error=str(e))
    obs.finish_span(span, status="error")
    raise
```

### CDN Configuration

```python
from cdn import CDNHelper, CachePolicy

# Initialize CDN helper with secret key for signed URLs
cdn = CDNHelper(secret_key="your-secret-key")

# Get headers for asset delivery with caching
headers, range_spec, status_code = cdn.get_asset_headers(
    content_type="image/gif",
    content_length=1024000,
    is_immutable=True,
    cache_duration=CachePolicy.IMMUTABLE_CACHE,
    range_header="bytes=0-1023"  # Optional: for partial content
)

# Create signed URL with expiration
signed_url = cdn.create_signed_asset_url(
    asset_url="https://gifdist.io/a/abc123def456",
    expiration_seconds=3600
)

# Validate signed URL
is_valid, error = cdn.validate_asset_url(signed_url)
if is_valid:
    print("URL is valid")
else:
    print(f"Invalid URL: {error}")
```

### Analytics Tracking

```python
from analytics import AnalyticsTracker, EventType, Platform

# Initialize the analytics tracker
tracker = AnalyticsTracker()

# Track events
tracker.track_event(
    asset_id="abc123def456",
    event_type=EventType.VIEW,
    platform=Platform.SLACK,
    short_code="Ab12Cd34"
)

tracker.track_event(
    asset_id="abc123def456",
    event_type=EventType.PLAY,
    platform=Platform.SLACK,
    short_code="Ab12Cd34"
)

# Get asset metrics
metrics = tracker.get_asset_metrics("abc123def456")
print(f"Views: {metrics['views']}")
print(f"Plays: {metrics['plays']}")
print(f"CTR: {metrics['ctr']}%")
print(f"Play Rate: {metrics['play_rate']}%")

# Get platform-specific metrics
platform_metrics = tracker.get_platform_metrics("abc123def456")
print(f"Slack metrics: {platform_metrics['slack']}")

# Get top performing assets
top_assets = tracker.get_top_assets(metric="ctr", limit=5)
for asset in top_assets:
    print(f"Asset {asset['asset_id']}: {asset['ctr']}% CTR")

# Get metrics for a specific short link
short_link_metrics = tracker.get_short_link_metrics("Ab12Cd34")
print(f"Short link views: {short_link_metrics['views']}")
print(f"Short link CTR: {short_link_metrics['ctr']}%")
```

### Rate Limiting

```python
from ratelimit import RateLimiter, RateLimitConfig, RateLimitStrategy, RateLimitError

# Configure rate limiter with token bucket strategy
config = RateLimitConfig(
    requests_per_window=100,  # 100 requests
    window_seconds=60,        # per 60 seconds
    strategy=RateLimitStrategy.TOKEN_BUCKET
)

limiter = RateLimiter(config, enable_per_ip=True, enable_per_user=True)

# Check if request is allowed
allowed, retry_after = limiter.check_rate_limit(
    ip_address="192.168.1.100",
    user_id="user_12345"
)

if allowed:
    print("Request allowed")
else:
    print(f"Rate limited. Retry after {retry_after:.1f} seconds")

# Enforce rate limit (raises exception if exceeded)
try:
    limiter.enforce_rate_limit(ip_address="192.168.1.100", user_id="user_12345")
    # Process request
except RateLimitError as e:
    print(f"Blocked: {e}")

# Get remaining quota
quota = limiter.get_remaining_quota(ip_address="192.168.1.100", user_id="user_12345")
print(f"IP quota: {quota.get('ip', 0)}, User quota: {quota.get('user', 0)}")
```

### Observability

```python
from observability import ObservabilityStack, LogLevel

# Initialize observability stack for your service
obs = ObservabilityStack(service_name="gif-api", min_log_level=LogLevel.INFO)

# Structured logging with trace context
obs.logger.info("Processing asset request", asset_id="abc123", user_id="user_789")
obs.logger.error("Upload failed", error="timeout", duration_ms=5000)

# Metrics collection
obs.metrics.increment_counter("asset.uploads", tags={"status": "success"})
obs.metrics.set_gauge("active_connections", 42)
obs.metrics.record_histogram("request.duration", 123.45, tags={"endpoint": "/upload"})

# Time operations automatically
with obs.metrics.time_operation("db_query", tags={"table": "assets"}):
    # Your database operation here
    pass

# Distributed tracing
span = obs.start_trace("handle_upload", asset_type="gif", user_tier="premium")
try:
    # Your operation here
    span.add_log("Validating asset")
    # ... more work ...
    obs.finish_span(span, status="success")
except Exception as e:
    span.add_log(f"Error: {e}", level="ERROR")
    obs.finish_span(span, status="error")

# Get dashboard data
dashboard = obs.get_dashboard_data()
print(f"Total logs: {dashboard['logs']['total']}")
print(f"Active traces: {dashboard['traces']['active']}")

# Query histogram statistics
stats = obs.metrics.get_histogram_stats("request.duration", tags={"endpoint": "/upload"})
print(f"p95: {stats['p95']}ms, p99: {stats['p99']}ms")
```

### AI Safety Scanning

```python
from ai_safety_scanner import AISafetyPipeline

# Initialize AI safety pipeline with OpenAI API
pipeline = AISafetyPipeline(
    api_key="your-openai-api-key",  # Or set OPENAI_API_KEY env var
    enable_vision=True  # Enable vision scanning for visual content
)

# Scan upload with both text and visual analysis
scan_results = pipeline.scan_upload(
    file_path="uploads/cat.gif",
    title="Funny Cat GIF",
    tags=["cat", "funny", "pets"],
    description="A hilarious cat doing backflips"
)

# Check if content is safe
is_safe, violations, confidence = pipeline.is_safe(scan_results)

if is_safe:
    print(f"Content approved with {confidence:.0%} confidence")
    # Proceed with upload
else:
    print(f"Content rejected: {', '.join(violations)}")
    # Block upload

# Inspect individual scan results
if "text" in scan_results:
    text_result = scan_results["text"]
    print(f"Text scan: {'Safe' if text_result.is_safe else 'Unsafe'}")
    print(f"Confidence: {text_result.confidence:.0%}")
    if text_result.violations:
        print(f"Violations: {', '.join(text_result.violations)}")

if "visual" in scan_results:
    visual_result = scan_results["visual"]
    print(f"Visual scan: {'Safe' if visual_result.is_safe else 'Unsafe'}")
    print(f"Confidence: {visual_result.confidence:.0%}")
    print(f"Description: {visual_result.metadata.get('description', '')}")
```

### Content Moderation

```python
from moderation import ModerationPipeline, ModerationDecision, ContentCategory

# Initialize moderation pipeline
pipeline = ModerationPipeline(
    strict_mode=True,              # Enable strict filtering
    auto_approve_threshold=0.95,   # Auto-approve above 95% confidence
    auto_reject_threshold=0.80,    # Auto-reject above 80% confidence
    enable_audit=True              # Enable audit trail
)

# Moderate content during upload
result = pipeline.moderate_content(
    asset_id="abc123def456",
    file_path="uploads/funny_cat.gif",
    file_hash="a1b2c3d4...",
    title="Funny Cat GIF",
    tags=["cat", "funny", "pets"],
    description="A hilarious cat doing backflips"
)

# Check moderation decision
if result.decision == ModerationDecision.APPROVED:
    print(f"Content approved with {result.confidence:.0%} confidence")
    # Proceed with upload
elif result.decision == ModerationDecision.REJECTED:
    print(f"Content rejected: {', '.join(result.reasons)}")
    # Block upload
elif result.decision == ModerationDecision.FLAGGED:
    print(f"Content flagged for manual review: {', '.join(result.reasons)}")
    # Queue for human review

# Manual review workflow
if result.decision == ModerationDecision.FLAGGED:
    # Human moderator reviews and makes decision
    audit_entry = pipeline.manual_review(
        asset_id="abc123def456",
        scan_id=result.scan_id,
        decision=ModerationDecision.APPROVED,
        reviewer_id="moderator_jane",
        notes="False positive - content is safe"
    )

# Get audit trail for compliance
audit_trail = pipeline.get_audit_trail(asset_id="abc123def456")
for entry in audit_trail:
    print(f"{entry.timestamp}: {entry.decision.value} by {entry.moderator}")

# Export audit trail for reporting
compliance_report = pipeline.export_audit_trail(
    start_time="2025-01-01T00:00:00",
    end_time="2025-12-31T23:59:59"
)

# Get moderation statistics
stats = pipeline.get_statistics()
print(f"Approval rate: {stats['approval_rate']:.1f}%")
print(f"Rejection rate: {stats['rejection_rate']:.1f}%")
print(f"Flag rate: {stats['flag_rate']:.1f}%")
```

## Testing

Run all tests:

```bash
pytest
```

Run specific test suites:

```bash
# Core module tests
pytest test_sharelinks.py test_analytics.py test_cdn.py test_observability.py test_ratelimit.py test_moderation.py test_ai_safety_scanner.py

# Integration tests
pytest test_integration.py test_integration_cross_module.py

# Edge case tests
pytest test_edge_cases_advanced.py test_cdn_edge_cases.py

# Security and performance tests
pytest test_security_analytics.py test_cdn_concurrency.py test_error_recovery.py
```

## API Reference

### ShareLinkGenerator

- `create_canonical_url(asset_id, asset_type="gif")`: Create canonical asset URL
- `create_share_link(asset_id, title="", tags=None)`: Generate short share link with metadata
- `resolve_short_link(short_code)`: Resolve short code to asset info (increments click counter)
- `generate_short_code()`: Generate unique 8-character short code
- `generate_hash_based_id(content_hash)`: Create deterministic asset ID from content hash
- `get_share_metadata(short_code)`: Get Open Graph metadata for share link

### AnalyticsTracker

- `track_event(asset_id, event_type, platform=Platform.WEB, short_code=None, metadata=None)`: Track analytics event
- `get_asset_metrics(asset_id)`: Get aggregated metrics (views, plays, clicks, ctr, play_rate, total_events)
- `get_platform_metrics(asset_id)`: Get metrics broken down by platform (views, plays, clicks, ctr, play_rate per platform)
- `get_short_link_metrics(short_code)`: Get metrics for a specific short link
- `get_top_assets(metric="views", limit=10)`: Get top performing assets by metric (supports: views, plays, clicks, ctr, play_rate)
- `get_events_by_timeframe(asset_id, start_time=None, end_time=None)`: Get events within timeframe
- `clear_events(asset_id=None)`: Clear events for an asset or all events if asset_id is None

### Enums

**EventType**: `VIEW`, `PLAY`, `CLICK`
**Platform**: `WEB`, `SLACK`, `DISCORD`, `TEAMS`, `TWITTER`, `FACEBOOK`, `OTHER`

### CDNHelper

- `get_asset_headers(content_type, content_length, is_immutable=False, cache_duration=CachePolicy.LONG_CACHE, range_header=None)`: Get complete headers for asset delivery (returns headers, range_spec, status_code)
- `create_signed_asset_url(asset_url, expiration_seconds=3600)`: Create a signed URL for secure asset access
- `validate_asset_url(url)`: Validate a signed asset URL (returns is_valid, error_message)

### CachePolicy

- `get_headers(cache_duration=LONG_CACHE, is_immutable=False, is_private=False)`: Generate cache control headers
- Cache duration constants: `IMMUTABLE_CACHE` (1 year), `LONG_CACHE` (24 hours), `SHORT_CACHE` (1 hour), `NO_CACHE` (0)

### RangeRequest

- `parse_range_header(range_header, content_length)`: Parse HTTP Range header and return (start, end) bytes
- `get_range_response_headers(start, end, total_length, content_type)`: Generate headers for partial content response
- `get_full_response_headers(total_length, content_type)`: Generate headers for full content response

### SignedURL

- `generate_signed_url(base_url, expiration_seconds=3600, additional_params=None)`: Generate signed URL with expiration
- `validate_signed_url(url)`: Validate signature and expiration (returns is_valid, error_message)

### RateLimiter

- `check_rate_limit(ip_address=None, user_id=None, count=1)`: Check if request is allowed (returns allowed, retry_after)
- `enforce_rate_limit(ip_address=None, user_id=None, count=1)`: Enforce limit, raises RateLimitError if exceeded
- `get_remaining_quota(ip_address=None, user_id=None)`: Get remaining quota for IP and/or user
- `reset_limits(ip_address=None, user_id=None)`: Reset limits for specific IP and/or user
- `clear_all()`: Clear all rate limit data

### RateLimitConfig

- `requests_per_window`: Number of requests allowed per window
- `window_seconds`: Window duration in seconds
- `strategy`: Rate limiting strategy (TOKEN_BUCKET, FIXED_WINDOW, SLIDING_WINDOW)

### RateLimitStrategy

- `TOKEN_BUCKET`: Smooth rate limiting with token refill
- `FIXED_WINDOW`: Fixed time windows with reset
- `SLIDING_WINDOW`: Rolling window for precise limiting

### Utility Functions

- `create_asset_hash(file_path)`: Generate SHA-256 hash of asset file for deduplication

### ObservabilityStack

- `start_trace(operation, **tags)`: Start a new distributed trace and return root span
- `finish_span(span, status="success")`: Finish a span with status (success/error)
- `get_dashboard_data()`: Get aggregated logs, metrics, and trace summaries

### StructuredLogger

- `debug(message, **metadata)`: Log debug message with metadata
- `info(message, **metadata)`: Log info message with metadata
- `warning(message, **metadata)`: Log warning message with metadata
- `error(message, **metadata)`: Log error message with metadata
- `critical(message, **metadata)`: Log critical message with metadata
- `get_logs(trace_id=None)`: Get log entries, optionally filtered by trace ID
- `clear_logs()`: Clear all stored logs

### MetricsCollector

- `increment_counter(name, value=1.0, tags=None)`: Increment a counter metric
- `set_gauge(name, value, tags=None)`: Set a gauge to a specific value
- `record_histogram(name, value, tags=None)`: Record a value in a histogram
- `time_operation(name, tags=None)`: Context manager for timing operations
- `get_counter(name, tags=None)`: Get current counter value
- `get_gauge(name, tags=None)`: Get current gauge value
- `get_histogram_stats(name, tags=None)`: Get histogram statistics (min, max, mean, median, p95, p99)
- `get_all_metrics()`: Get all recorded metrics
- `clear_metrics()`: Clear all metrics

### Tracer

- `start_trace(operation, tags=None)`: Start a new trace (root span)
- `start_span(operation, parent_span, tags=None)`: Start a child span
- `finish_span(span, status="success")`: Finish a span
- `get_trace(trace_id)`: Get all spans for a trace
- `get_all_traces()`: Get all traces
- `clear_traces()`: Clear all traces

### Span (Tracing)

- `finish(status="success")`: Complete the span
- `add_log(message, level="INFO", **kwargs)`: Add a log entry to the span
- `to_dict()`: Convert span to dictionary

### AISafetyPipeline

- `scan_upload(file_path=None, title="", tags=None, description="")`: Perform complete safety scan on upload (returns dict with 'text' and optionally 'visual' SafetyScanResult)
- `is_safe(scan_results)`: Determine if content is safe based on all scan results (returns tuple of is_safe, violations, confidence)

### OpenAIModerationScanner

- `scan_text(text)`: Scan text content using OpenAI Moderation API (returns SafetyScanResult)

### OpenAIVisionScanner

- `scan_image(file_path, check_nsfw=True)`: Scan image/GIF using OpenAI Vision API (returns SafetyScanResult)

### SafetyScanResult

- `is_safe` (bool): Whether content is safe
- `confidence` (float): Confidence score 0.0 to 1.0
- `violations` (list): List of violation descriptions
- `categories_flagged` (dict): Category name to score mapping
- `metadata` (dict): Additional scan metadata

### ModerationPipeline

- `moderate_content(asset_id, file_path, file_hash, title="", tags=None, description="", metadata=None)`: Moderate content through complete pipeline (returns ModerationResult)
- `manual_review(asset_id, scan_id, decision, reviewer_id, notes="")`: Record manual review decision (returns AuditEntry)
- `get_audit_trail(asset_id=None, decision=None, limit=100)`: Get audit trail entries with optional filters
- `get_statistics()`: Get moderation statistics (total_scans, approved, rejected, flagged, approval_rate, rejection_rate, flag_rate)
- `clear_audit_trail(asset_id=None)`: Clear audit trail for specific asset or all
- `export_audit_trail(start_time=None, end_time=None)`: Export audit trail for compliance reporting

### ModerationDecision (Enum)

- `APPROVED`: Content approved and safe to publish
- `REJECTED`: Content rejected due to policy violations
- `FLAGGED`: Content flagged for manual review
- `PENDING`: Content pending moderation

### ContentCategory (Enum)

- `SAFE`: Safe for work content
- `NSFW`: Not safe for work content
- `GRAPHIC_VIOLENCE`: Graphic violence detected
- `HATE_SPEECH`: Hate speech detected
- `ILLEGAL`: Illegal content detected
- `SPAM`: Spam content detected
- `UNKNOWN`: Content requires manual classification

### ContentScanner

- `scan_metadata(title="", tags=None, description="")`: Scan text metadata for inappropriate content (returns category, confidence, reasons)
- `scan_visual_content(file_path, file_hash)`: Scan visual content using AI/ML service (returns category, confidence, reasons)