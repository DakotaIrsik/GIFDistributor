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

## Installation

```bash
pip install -r requirements.txt
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

## Testing

Run the test suite:

```bash
pytest test_sharelinks.py test_analytics.py test_cdn.py test_integration.py
```

Or run all tests at once:

```bash
pytest
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

### Utility Functions

- `create_asset_hash(file_path)`: Generate SHA-256 hash of asset file for deduplication