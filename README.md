# GIFDistributor

A system for distributing and sharing GIF assets with short links and canonical URLs.

## Security Features

### OIDC Authentication
- **Zero Long-Lived Tokens**: Uses OpenID Connect (OIDC) for Cloudflare deployments
- **Automatic Token Rotation**: Tokens expire after each workflow run
- **Enhanced Audit Trail**: Full identity verification for all deployments
- **Reduced Attack Surface**: No secrets to leak or steal

See [OIDC Setup Guide](docs/oidc-cloudflare-setup.md) for configuration details.

### Secrets Hygiene
- Automated rotation reminders for API keys (90-day schedule)
- Weekly secrets hygiene audits
- Environment-based secret protection
- Comprehensive monitoring and incident response

See [Secrets Management Guide](docs/secrets-management.md) for best practices.

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
- **Media Jobs Runtime**: Asynchronous job queue with ffmpeg support and autoscaling worker pool for media processing tasks
- **GIPHY Publisher**: Channel management and programmatic upload to GIPHY with tagging and content rating support
- **Tenor Publisher**: Partner API integration for uploading GIFs to Tenor with metadata and tag optimization
- **Cloudflare Infrastructure**: R2 storage, Workers for API, Pages for web app, KV for metadata, and Durable Objects for real-time features
- **Advertising & Monetization**: Website display ads for Free tier (Google AdSense, custom networks) with ad-free Pro/Team tiers
- **Clean Media Guarantee**: NO watermarks or embedded ads in media files - all GIF/MP4/WebP remain 100% clean and shareable
- **Discord Integration**: OAuth2 authentication and bot functionality for sending GIF embeds and attachments to Discord channels

## Installation

### Python Modules

```bash
pip install -r requirements.txt

# For AI safety scanning (optional):
pip install openai pillow
```

### Cloudflare Infrastructure

```bash
# Install Wrangler CLI
npm install -g wrangler

# Authenticate with Cloudflare
wrangler login

# Create R2 buckets (staging + production)
npm run cf:buckets:create

# Create KV namespaces
npm run cf:kv:create

# Deploy to staging
npm run deploy:staging

# Deploy to production
npm run deploy:production
```

See [Cloudflare Infrastructure Guide](docs/cloudflare-infrastructure.md) for detailed setup instructions.

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:

- `OPENAI_API_KEY` - OpenAI API key for AI safety scanning ([Get your key](https://platform.openai.com/api-keys))
- `NODE_ENV` - Application environment (development/staging/production)
- `DISCORD_CLIENT_ID` - Discord application client ID (for OAuth2)
- `DISCORD_CLIENT_SECRET` - Discord application client secret (for OAuth2)
- `DISCORD_BOT_TOKEN` - Discord bot token (optional, for bot-based messaging)

See `.env.example` for all available configuration options.

### GitHub Actions Secrets

For CI/CD and production deployments, configure secrets in GitHub:

1. **Production Environment**: Settings → Environments → production
   - Add secret: `OPENAI_API_KEY` (production key)
   - Enable protection rules

2. **Development Environment**: Settings → Environments → development
   - Add secret: `OPENAI_API_KEY` (development key)

See [.github/SECRETS_SETUP.md](.github/SECRETS_SETUP.md) for detailed setup instructions.

### Secret Rotation

Secrets should be rotated every 90 days. An automated workflow checks rotation status monthly and creates reminder issues.

See [docs/secrets-management.md](docs/secrets-management.md) for the complete rotation process.

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

### Media Jobs Runtime

```python
from media_jobs import MediaJobQueue, JobPriority, JobStatus, create_transcode_job, create_thumbnail_job

# Initialize job queue with autoscaling
queue = MediaJobQueue(
    min_workers=2,           # Minimum worker threads
    max_workers=10,          # Maximum worker threads
    scale_up_threshold=5,    # Scale up when queue has 5+ jobs
    scale_down_threshold=2   # Scale down when queue has <2 jobs
)

# Submit a custom media processing job
job_id = queue.submit_job(
    job_type="transcode",
    input_path="input.mp4",
    output_path="output.mp4",
    ffmpeg_args=["-i", "input.mp4", "-c:v", "libx264", "-c:a", "aac", "output.mp4"],
    priority=JobPriority.HIGH,
    timeout_seconds=300
)

# Or use convenience functions
transcode_job_id = create_transcode_job(
    queue=queue,
    input_path="video.mp4",
    output_path="video_h264.mp4",
    video_codec="libx264",
    audio_codec="aac",
    bitrate="2M",
    priority=JobPriority.CRITICAL
)

thumbnail_job_id = create_thumbnail_job(
    queue=queue,
    input_path="video.mp4",
    output_path="thumbnail.jpg",
    timestamp="00:00:05",
    width=640,
    priority=JobPriority.NORMAL
)

# Check job status
job = queue.get_job_status(job_id)
print(f"Status: {job.status.value}")
print(f"Started: {job.started_at}")
print(f"Completed: {job.completed_at}")

# Get worker pool metrics
metrics = queue.get_metrics()
print(f"Active workers: {metrics.active_workers}")
print(f"Queue size: {metrics.queue_size}")
print(f"Jobs processed: {metrics.total_jobs_processed}")
print(f"Avg duration: {metrics.average_job_duration:.2f}s")

# Cancel a pending job
if queue.cancel_job(job_id):
    print("Job cancelled")

# Graceful shutdown
queue.shutdown(wait=True)
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

### GIPHY Publisher

```python
from giphy_publisher import (
    GiphyPublisher,
    GiphyUploadMetadata,
    GiphyContentRating,
    GiphyChannel,
    GiphyChannelType
)

# Initialize GIPHY publisher
publisher = GiphyPublisher(
    api_key="your-giphy-api-key",
    username="your-giphy-username",
    sfw_only=True  # Enforce G/PG ratings only
)

# Create and configure a channel
channel = GiphyChannel(
    channel_id="my_brand_channel",
    display_name="My Brand",
    channel_type=GiphyChannelType.BRAND,
    slug="my-brand",
    description="Official GIFs from My Brand",
    is_verified=False
)
publisher.create_channel(channel)

# Prepare upload metadata
metadata = GiphyUploadMetadata(
    media_url="https://cdn.example.com/my-gif.gif",
    title="Funny Cat Reaction",
    tags=["cat", "funny", "reaction", "animals"],
    content_rating=GiphyContentRating.G,
    source_url="https://example.com/source",
    channel_id="my_brand_channel"
)

# Upload to GIPHY
result = publisher.upload(metadata)

if result.success:
    print(f"Upload successful!")
    print(f"GIPHY ID: {result.giphy_id}")
    print(f"GIPHY URL: {result.giphy_url}")
    print(f"Embed URL: {result.embed_url}")
else:
    print(f"Upload failed: {result.error_message}")

# Check upload status
status = publisher.check_upload_status(result.giphy_id)
print(f"Status: {status['status']}")
print(f"Views: {status['views']}")

# Get user statistics
stats = publisher.get_user_stats()
print(f"Total uploads: {stats['total_uploads']}")
print(f"Upload limit remaining: {stats['upload_limit_remaining']}")

# Batch upload multiple GIFs
batch_metadata = [
    GiphyUploadMetadata(
        media_url=f"https://cdn.example.com/gif-{i}.gif",
        title=f"GIF {i}",
        tags=["batch", "upload", f"gif{i}"]
    )
    for i in range(5)
]

batch_results = publisher.batch_upload(batch_metadata)
successful = sum(1 for r in batch_results if r.success)
print(f"Uploaded {successful}/{len(batch_results)} GIFs")
```

### Tenor Publisher

```python
from tenor_publisher import (
    TenorPublisher,
    TenorUploadMetadata,
    TenorContentRating
)

# Initialize Tenor publisher
publisher = TenorPublisher(
    api_key="your-tenor-api-key",
    partner_id="your-partner-id",
    sfw_only=True  # Enforce HIGH (G-rated) content only
)

# Prepare upload metadata
metadata = TenorUploadMetadata(
    media_url="https://cdn.example.com/my-gif.gif",
    title="Excited Dance",
    tags=["dance", "excited", "celebration"],
    content_rating=TenorContentRating.HIGH,
    source_id="asset_12345",
    source_url="https://example.com/source"
)

# Upload to Tenor
result = publisher.upload(metadata)

if result.success:
    print(f"Upload successful!")
    print(f"Tenor ID: {result.tenor_id}")
    print(f"Tenor URL: {result.tenor_url}")
else:
    print(f"Upload failed: {result.error_message}")

# Get partner statistics
stats = publisher.get_partner_stats()
print(f"Total uploads: {stats['total_uploads']}")
print(f"Upload limit remaining: {stats['upload_limit_remaining']}")

# Format tags for optimal reach
tags = ["Funny Cat", "REACTION", "Cute Animals"]
formatted_tags = publisher.format_tags_for_tenor(tags)
reach_estimate = publisher.estimate_tag_reach(formatted_tags)
print(f"Estimated monthly searches: {reach_estimate['estimated_monthly_searches']}")

# Batch upload
batch_results = publisher.batch_upload([
    TenorUploadMetadata(
        media_url=f"https://cdn.example.com/tenor-{i}.gif",
        title=f"Tenor GIF {i}",
        tags=["tenor", "batch", f"gif{i}"]
    )
    for i in range(3)
])
```

## Testing

Run all tests:

```bash
pytest
```

Run specific test suites:

```bash
# Core module tests
pytest test_sharelinks.py test_analytics.py test_cdn.py test_observability.py test_ratelimit.py test_moderation.py test_ai_safety_scanner.py test_media_jobs.py

# Integration tests
pytest test_integration.py test_integration_cross_module.py test_observability_integration.py

# Edge case and advanced tests
pytest test_edge_cases_advanced.py test_cdn_edge_cases.py test_observability_advanced.py

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

### MediaJobQueue

- `submit_job(job_type, input_path, output_path, ffmpeg_args, priority=JobPriority.NORMAL, timeout_seconds=300, metadata=None)`: Submit a media processing job (returns job_id)
- `get_job_status(job_id)`: Get job status and details by ID
- `cancel_job(job_id)`: Cancel a pending job (returns True if cancelled)
- `get_metrics()`: Get worker pool metrics (active workers, queue size, jobs processed, average duration)
- `shutdown(wait=True)`: Shutdown the job queue and workers

### FFmpegRuntime

- `execute_ffmpeg(args, timeout_seconds=300)`: Execute ffmpeg command with timeout (returns returncode, stdout, stderr)
- `probe_media(file_path)`: Get media file information using ffprobe (returns metadata dict)

### MediaJob

- `job_id`: Unique job identifier
- `job_type`: Type of job (e.g., 'transcode', 'thumbnail')
- `status`: Current job status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- `priority`: Job priority (CRITICAL, HIGH, NORMAL, LOW)
- `created_at`, `started_at`, `completed_at`: Timestamps
- `error`: Error message if job failed
- `metadata`: Additional job metadata

### Job Helper Functions

- `create_transcode_job(queue, input_path, output_path, video_codec="libx264", audio_codec="aac", bitrate="1M", priority=JobPriority.NORMAL)`: Create a video transcoding job
- `create_thumbnail_job(queue, input_path, output_path, timestamp="00:00:01", width=320, priority=JobPriority.NORMAL)`: Create a thumbnail extraction job