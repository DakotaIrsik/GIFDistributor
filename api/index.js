/**
 * GIFDistributor API - Cloudflare Worker
 *
 * Main entry point for the API running on Cloudflare Workers.
 * Handles asset uploads, short links, analytics, and CDN operations.
 */

// CORS headers for cross-origin requests
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*', // TODO: Restrict to specific domains in production
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, Range',
  'Access-Control-Max-Age': '86400',
};

// Handle CORS preflight requests
function handleOptions() {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

// Main request router
async function handleRequest(request, env, ctx) {
  const url = new URL(request.url);
  const path = url.pathname;

  // CORS preflight
  if (request.method === 'OPTIONS') {
    return handleOptions();
  }

  // API routes
  if (path === '/' || path === '/health') {
    return handleHealth(env);
  }

  if (path.startsWith('/upload')) {
    return handleUpload(request, env, ctx);
  }

  if (path.startsWith('/a/')) {
    return handleAssetRequest(request, env, path);
  }

  if (path.startsWith('/s/')) {
    return handleShortLink(request, env, path);
  }

  if (path.startsWith('/analytics')) {
    return handleAnalytics(request, env);
  }

  // 404 for unknown routes
  return new Response('Not Found', {
    status: 404,
    headers: CORS_HEADERS,
  });
}

// Health check endpoint
function handleHealth(env) {
  return new Response(JSON.stringify({
    status: 'healthy',
    service: 'gifdistributor-api',
    environment: env.ENVIRONMENT || 'development',
    timestamp: new Date().toISOString(),
  }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}

// Handle file upload (direct to R2)
async function handleUpload(request, env, ctx) {
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', {
      status: 405,
      headers: CORS_HEADERS,
    });
  }

  try {
    // Get upload data
    const formData = await request.formData();
    const file = formData.get('file');

    if (!file) {
      return new Response(JSON.stringify({ error: 'No file provided' }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          ...CORS_HEADERS,
        },
      });
    }

    // Generate asset ID (hash-based for deduplication)
    const arrayBuffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const assetId = hashArray.map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 16);

    // Upload to R2
    const key = `assets/${assetId}`;
    await env.MEDIA_BUCKET.put(key, arrayBuffer, {
      httpMetadata: {
        contentType: file.type,
      },
    });

    // Store metadata in KV
    const metadata = {
      asset_id: assetId,
      filename: file.name,
      content_type: file.type,
      size: file.size,
      uploaded_at: new Date().toISOString(),
    };

    await env.SHARE_LINKS.put(`asset:${assetId}`, JSON.stringify(metadata));

    return new Response(JSON.stringify({
      asset_id: assetId,
      canonical_url: `${env.CDN_BASE_URL}/a/${assetId}`,
      size: file.size,
    }), {
      status: 201,
      headers: {
        'Content-Type': 'application/json',
        ...CORS_HEADERS,
      },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...CORS_HEADERS,
      },
    });
  }
}

// Handle canonical asset requests
async function handleAssetRequest(request, env, path) {
  const assetId = path.substring(3); // Remove '/a/'

  try {
    // Get asset from R2
    const object = await env.MEDIA_BUCKET.get(`assets/${assetId}`);

    if (!object) {
      return new Response('Asset Not Found', {
        status: 404,
        headers: CORS_HEADERS,
      });
    }

    // Handle Range requests for partial content
    const range = request.headers.get('Range');

    if (range) {
      return handleRangeRequest(object, range);
    }

    // Return full asset
    return new Response(object.body, {
      headers: {
        'Content-Type': object.httpMetadata.contentType || 'application/octet-stream',
        'Cache-Control': 'public, max-age=31536000, immutable',
        'ETag': object.httpEtag,
        ...CORS_HEADERS,
      },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...CORS_HEADERS,
      },
    });
  }
}

// Handle HTTP Range requests
function handleRangeRequest(object, rangeHeader) {
  const match = rangeHeader.match(/bytes=(\d+)-(\d*)/);
  if (!match) {
    return new Response('Invalid Range', { status: 416 });
  }

  const start = parseInt(match[1]);
  const end = match[2] ? parseInt(match[2]) : object.size - 1;

  // Note: This is simplified - R2 doesn't support range requests directly yet
  // In production, you'd need to stream and slice the response
  return new Response(object.body, {
    status: 206,
    headers: {
      'Content-Type': object.httpMetadata.contentType,
      'Content-Range': `bytes ${start}-${end}/${object.size}`,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000',
      ...CORS_HEADERS,
    },
  });
}

// Handle short link redirects
async function handleShortLink(request, env, path) {
  const shortCode = path.substring(3); // Remove '/s/'

  try {
    // Get short link data from KV
    const linkData = await env.SHARE_LINKS.get(`short:${shortCode}`);

    if (!linkData) {
      return new Response('Short Link Not Found', {
        status: 404,
        headers: CORS_HEADERS,
      });
    }

    const data = JSON.parse(linkData);

    // Increment click counter (async, don't wait)
    const clicks = (data.clicks || 0) + 1;
    data.clicks = clicks;
    env.ctx.waitUntil(
      env.SHARE_LINKS.put(`short:${shortCode}`, JSON.stringify(data))
    );

    // Track analytics event (async)
    env.ctx.waitUntil(
      trackEvent(env, data.asset_id, 'CLICK', 'SHORT_LINK', { short_code: shortCode })
    );

    // Redirect to canonical URL
    return Response.redirect(`${env.CDN_BASE_URL}/a/${data.asset_id}`, 302);
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...CORS_HEADERS,
      },
    });
  }
}

// Handle analytics requests
async function handleAnalytics(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;

  if (path === '/analytics/track' && request.method === 'POST') {
    try {
      const data = await request.json();
      await trackEvent(env, data.asset_id, data.event_type, data.platform, data.metadata);

      return new Response(JSON.stringify({ success: true }), {
        headers: {
          'Content-Type': 'application/json',
          ...CORS_HEADERS,
        },
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          ...CORS_HEADERS,
        },
      });
    }
  }

  if (path.startsWith('/analytics/metrics/')) {
    const assetId = path.substring('/analytics/metrics/'.length);

    try {
      // Get cached metrics from KV
      const cachedMetrics = await env.ANALYTICS_CACHE.get(`metrics:${assetId}`);

      if (cachedMetrics) {
        return new Response(cachedMetrics, {
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=300',
            ...CORS_HEADERS,
          },
        });
      }

      // If not cached, return empty metrics
      const emptyMetrics = {
        asset_id: assetId,
        views: 0,
        plays: 0,
        clicks: 0,
        ctr: 0,
      };

      return new Response(JSON.stringify(emptyMetrics), {
        headers: {
          'Content-Type': 'application/json',
          ...CORS_HEADERS,
        },
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...CORS_HEADERS,
        },
      });
    }
  }

  return new Response('Not Found', {
    status: 404,
    headers: CORS_HEADERS,
  });
}

// Track analytics event
async function trackEvent(env, assetId, eventType, platform, metadata = {}) {
  const event = {
    asset_id: assetId,
    event_type: eventType,
    platform: platform,
    timestamp: new Date().toISOString(),
    metadata: metadata,
  };

  // Store event in KV (for now, in production use Durable Objects or external analytics)
  const eventKey = `event:${assetId}:${Date.now()}:${Math.random().toString(36).substr(2, 9)}`;
  await env.ANALYTICS_CACHE.put(eventKey, JSON.stringify(event), {
    expirationTtl: 86400, // 24 hours
  });
}

// Export the Worker
export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, env, { ...ctx, ctx });
  },
};
