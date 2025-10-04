# Publisher UI Module

**Issue:** #38
**Slug:** `publisher-ui`
**Dependencies:** Issue #14 (direct upload), Issue #48 (shortlinks)

## Overview

The Publisher UI provides a streamlined two-step workflow for uploading media files and distributing them across multiple platforms. This is the simplified "quick publish" flow, distinct from the full wizard workflow (Issue #39) which includes metadata/tagging steps.

## Architecture

### Route
- **Path:** `/publisher`
- **Component:** `web/src/app/publisher/page.tsx`

### Workflow Steps

#### Step 1: Upload
**Component:** `SimpleUploadStep.tsx`

Features:
- Drag-and-drop file upload
- File type validation (GIF, MP4, WebM, WebP)
- File size display
- Upload progress indicator
- Resumable chunked upload support
- SHA-256 deduplication (via `direct_upload.py`)

Supported file types:
- `image/gif`
- `video/mp4`
- `video/webm`
- `image/webp`

Max file size: 100 MB

#### Step 2: Choose Platforms
**Component:** `SimplePlatformStep.tsx`

Features:
- Multi-select platform chooser
- Platform availability status
- Requirements info for each platform
- File preview summary
- Selection summary

Supported Platforms:
1. **GIPHY** - Largest GIF platform with searchable library
2. **Tenor** - Google-owned GIF library
3. **Slack** - Post to channels with hosted media
4. **Discord** - Share in servers as embeds
5. **Microsoft Teams** - Distribute via message extension

## User Flow

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────┐
│   Upload    │ ───> │ Choose Platforms │ ───> │  Distribute  │
│   Media     │      │                  │      │   (Submit)   │
└─────────────┘      └──────────────────┘      └──────────────┘
```

1. User uploads media file (drag-and-drop or browse)
2. File is validated and uploaded with progress indication
3. User selects target distribution platforms
4. User clicks "Distribute Now" to publish

## Integration Points

### Backend Dependencies

**Direct Upload Module** (`direct_upload.py` - Issue #14)
- Resumable chunked upload
- SHA-256 deduplication
- Signed URL generation
- File validation

**Shortlinks Module** (`sharelinks.py` - Issue #48)
- Generate canonical URLs for uploaded media
- Platform-specific short URLs
- Asset URL management

### Platform Publishers

Each platform requires its own publisher module:
- `giphy_publisher.py` (Issue #12)
- `tenor_publisher.py` (Issue #28)
- Slack integration (Issue #26, #41)
- Discord integration (Issue #9, #46)
- Teams integration (Issue #42, #43)

## API Endpoints

The Publisher UI interacts with the following API routes:

### Upload
```
POST /api/upload
Content-Type: multipart/form-data

Body:
  - file: File (binary)
  - resumable_session_id: string (optional)

Response:
{
  "file_url": "https://cdn.example.com/media/abc123.gif",
  "file_id": "abc123",
  "size": 1048576,
  "type": "image/gif",
  "sha256": "..."
}
```

### Distribute
```
POST /api/distribute
Content-Type: application/json

Body:
{
  "file_id": "abc123",
  "file_url": "https://cdn.example.com/media/abc123.gif",
  "platforms": ["giphy", "tenor", "slack"]
}

Response:
{
  "status": "queued",
  "job_id": "dist_xyz789",
  "platforms": {
    "giphy": { "status": "pending", "job_id": "..." },
    "tenor": { "status": "pending", "job_id": "..." },
    "slack": { "status": "pending", "job_id": "..." }
  }
}
```

## UI Components

### SimpleUploadStep
**Props:**
- `onNext: (file: File, uploadedUrl: string) => void`

**State:**
- File selection
- Upload progress
- Drag-and-drop handling

**Features:**
- Visual file type icons (🎬 for video, 🖼️ for images)
- Progress bar during upload
- File size validation
- Informational message about resumable uploads

### SimplePlatformStep
**Props:**
- `file: File | null`
- `uploadedFileUrl: string`
- `selectedPlatforms: string[]`
- `onNext: (platforms: string[]) => void`
- `onBack: () => void`

**State:**
- Platform selection (multi-select)
- Platform details expansion

**Features:**
- Platform cards with icons and descriptions
- Requirements info (expandable)
- "Coming soon" status badges
- Selected platforms summary
- Disabled state when no platforms selected

## Styling

The UI uses inline styles for simplicity and portability:
- Primary color: `#0070f3` (blue)
- Border radius: `6px` to `8px`
- Responsive layout with `maxWidth: 800px`
- Hover states and transitions
- Accessible color contrasts

## Future Enhancements

1. **Real Upload Integration**
   - Connect to actual `/api/upload` endpoint
   - Implement resumable upload protocol
   - Add retry logic for failed uploads

2. **Real Distribution Integration**
   - Connect to `/api/distribute` endpoint
   - Show distribution status/progress
   - Handle platform-specific errors

3. **Platform Authentication**
   - OAuth flows for each platform
   - Credential management
   - Account linking UI

4. **Advanced Features**
   - Batch upload support
   - Schedule publishing
   - Platform-specific settings
   - Distribution analytics

## Testing

### Manual Testing
1. Navigate to `/publisher`
2. Upload a test GIF/MP4 file
3. Verify progress indicator
4. Select multiple platforms
5. Click "Distribute Now"
6. Verify alert shows selected platforms

### Automated Testing (Future)
- Component unit tests with Jest/React Testing Library
- E2E tests with Playwright/Cypress
- Upload flow integration tests

## Related Issues

- **Issue #39:** Full publisher wizard (upload → metadata → platforms → distribute)
- **Issue #14:** Direct browser upload with resumable capability
- **Issue #48:** Shortlinks and canonical URLs
- **Issue #12:** GIPHY publisher integration
- **Issue #28:** Tenor publisher integration
- **Issue #26, #41:** Slack integration
- **Issue #9, #46:** Discord integration
- **Issue #42, #43:** Microsoft Teams integration

## Notes

- This UI is designed for quick, streamlined publishing without metadata/tagging
- For full control with metadata, users should use the `/publish` route (Issue #39)
- The upload step uses simulated progress; production should integrate with `direct_upload.py`
- Platform distribution is currently mocked; production needs queue integration
