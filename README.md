# GIFDistributor

A system for distributing and sharing GIF assets with short links and canonical URLs.

## Features

- **Share Links**: Generate short, shareable links for GIF assets (`/s/{short_code}`)
- **Canonical URLs**: Persistent asset URLs (`/a/{asset_id}`)
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

# Get platform-specific metrics
platform_metrics = tracker.get_platform_metrics("abc123def456")
print(f"Slack metrics: {platform_metrics['slack']}")

# Get top performing assets
top_assets = tracker.get_top_assets(metric="ctr", limit=5)
```

## Testing

Run the test suite:

```bash
pytest test_sharelinks.py test_analytics.py
```

## API Reference

### ShareLinkGenerator

- `create_canonical_url(asset_id, asset_type="gif")`: Create canonical asset URL
- `create_share_link(asset_id, title="", tags=None)`: Generate short share link
- `resolve_short_link(short_code)`: Resolve short code to asset info
- `generate_hash_based_id(content_hash)`: Create deterministic asset ID
- `get_share_metadata(short_code)`: Get Open Graph metadata

### AnalyticsTracker

- `track_event(asset_id, event_type, platform, short_code, metadata)`: Track analytics event
- `get_asset_metrics(asset_id)`: Get aggregated metrics (views, plays, clicks, CTR)
- `get_platform_metrics(asset_id)`: Get metrics broken down by platform
- `get_short_link_metrics(short_code)`: Get metrics for a specific short link
- `get_top_assets(metric, limit)`: Get top performing assets by metric
- `get_events_by_timeframe(asset_id, start_time, end_time)`: Get events within timeframe
- `clear_events(asset_id)`: Clear events for an asset or all events

### Utility Functions

- `create_asset_hash(file_path)`: Generate SHA-256 hash of asset file