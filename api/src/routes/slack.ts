/**
 * Slack App Routes - OAuth + Message Posting
 * Issue: #26
 *
 * Provides OAuth 2.0 flow for Slack workspace integration
 * and API endpoints for posting GIFs to Slack channels
 */

import express, { Request, Response } from 'express';
import axios from 'axios';
import crypto from 'crypto';

const router = express.Router();

// Environment variables
const SLACK_CLIENT_ID = process.env.SLACK_CLIENT_ID;
const SLACK_CLIENT_SECRET = process.env.SLACK_CLIENT_SECRET;
const SLACK_REDIRECT_URI = process.env.SLACK_REDIRECT_URI || 'http://localhost:3001/api/slack/oauth/callback';
const SLACK_SIGNING_SECRET = process.env.SLACK_SIGNING_SECRET;

// In-memory token storage (should be replaced with database in production)
const workspaceTokens: Map<string, {
  access_token: string;
  team_id: string;
  team_name: string;
  bot_user_id: string;
  scope: string;
}> = new Map();

/**
 * OAuth installation URL - redirects users to Slack's OAuth page
 */
router.get('/install', (req: Request, res: Response) => {
  if (!SLACK_CLIENT_ID) {
    return res.status(500).json({ error: 'Slack client ID not configured' });
  }

  const state = crypto.randomBytes(16).toString('hex');
  const scopes = [
    'chat:write',           // Post messages
    'files:write',          // Upload files
    'links:write',          // Unfurl links
    'channels:read',        // Read channel info
    'groups:read',          // Read private channel info
    'im:read',              // Read DM info
    'mpim:read'             // Read group DM info
  ].join(',');

  const authUrl = `https://slack.com/oauth/v2/authorize?client_id=${SLACK_CLIENT_ID}&scope=${scopes}&redirect_uri=${encodeURIComponent(SLACK_REDIRECT_URI)}&state=${state}`;

  // In production, store state in session/database for CSRF protection
  res.redirect(authUrl);
});

/**
 * OAuth callback - handles the redirect from Slack after user approves
 */
router.get('/oauth/callback', async (req: Request, res: Response) => {
  const { code, state, error } = req.query;

  if (error) {
    return res.status(400).json({
      error: 'OAuth authorization failed',
      details: error
    });
  }

  if (!code) {
    return res.status(400).json({ error: 'No authorization code received' });
  }

  if (!SLACK_CLIENT_ID || !SLACK_CLIENT_SECRET) {
    return res.status(500).json({ error: 'Slack OAuth credentials not configured' });
  }

  try {
    // Exchange code for access token
    const tokenResponse = await axios.post('https://slack.com/api/oauth.v2.access',
      new URLSearchParams({
        client_id: SLACK_CLIENT_ID,
        client_secret: SLACK_CLIENT_SECRET,
        code: code as string,
        redirect_uri: SLACK_REDIRECT_URI
      }).toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    if (!tokenResponse.data.ok) {
      return res.status(400).json({
        error: 'Failed to exchange code for token',
        details: tokenResponse.data.error
      });
    }

    const { access_token, team, authed_user, scope } = tokenResponse.data;

    // Store token (in production, store in database)
    workspaceTokens.set(team.id, {
      access_token,
      team_id: team.id,
      team_name: team.name,
      bot_user_id: tokenResponse.data.bot_user_id,
      scope
    });

    res.json({
      success: true,
      team: team.name,
      message: 'Successfully installed GIF Distributor to your Slack workspace'
    });

  } catch (err: any) {
    console.error('OAuth callback error:', err);
    res.status(500).json({
      error: 'Failed to complete OAuth flow',
      details: err.message
    });
  }
});

/**
 * Verify Slack request signature for security
 */
function verifySlackSignature(
  signature: string,
  timestamp: string,
  body: string
): boolean {
  if (!SLACK_SIGNING_SECRET) {
    return false;
  }

  const time = Math.floor(Date.now() / 1000);
  if (Math.abs(time - parseInt(timestamp)) > 300) {
    // Request is older than 5 minutes
    return false;
  }

  const sigBasestring = `v0:${timestamp}:${body}`;
  const mySignature = 'v0=' + crypto
    .createHmac('sha256', SLACK_SIGNING_SECRET)
    .update(sigBasestring)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(mySignature),
    Buffer.from(signature)
  );
}

/**
 * Post a message with hosted GIF to a Slack channel
 */
router.post('/post-message', async (req: Request, res: Response) => {
  const { team_id, channel_id, gif_url, title, tags } = req.body;

  if (!team_id || !channel_id || !gif_url) {
    return res.status(400).json({
      error: 'Missing required fields: team_id, channel_id, gif_url'
    });
  }

  const workspace = workspaceTokens.get(team_id);
  if (!workspace) {
    return res.status(401).json({
      error: 'Workspace not authenticated. Please install the app first.'
    });
  }

  try {
    // Build message with attachment
    const message: any = {
      channel: channel_id,
      text: title || 'Check out this GIF!',
      attachments: [
        {
          fallback: title || 'GIF from GIF Distributor',
          image_url: gif_url,
          color: '#FF6B35'
        }
      ]
    };

    // Add tags as footer if provided
    if (tags && Array.isArray(tags) && tags.length > 0) {
      message.attachments[0].footer = `Tags: ${tags.join(', ')}`;
    }

    // Post message using Slack Web API
    const response = await axios.post(
      'https://slack.com/api/chat.postMessage',
      message,
      {
        headers: {
          'Authorization': `Bearer ${workspace.access_token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.data.ok) {
      return res.status(400).json({
        error: 'Failed to post message',
        details: response.data.error
      });
    }

    res.json({
      success: true,
      message_ts: response.data.ts,
      channel: response.data.channel
    });

  } catch (err: any) {
    console.error('Post message error:', err);
    res.status(500).json({
      error: 'Failed to post message to Slack',
      details: err.message
    });
  }
});

/**
 * Upload a file directly to Slack (alternative to hosted GIF)
 */
router.post('/upload-file', async (req: Request, res: Response) => {
  const { team_id, channel_id, file_url, filename, title, comment } = req.body;

  if (!team_id || !channel_id || !file_url) {
    return res.status(400).json({
      error: 'Missing required fields: team_id, channel_id, file_url'
    });
  }

  const workspace = workspaceTokens.get(team_id);
  if (!workspace) {
    return res.status(401).json({
      error: 'Workspace not authenticated. Please install the app first.'
    });
  }

  try {
    // Download file from URL
    const fileResponse = await axios.get(file_url, {
      responseType: 'arraybuffer'
    });
    const fileBuffer = Buffer.from(fileResponse.data);

    // Upload file to Slack
    const FormData = require('form-data');
    const formData = new FormData();
    formData.append('file', fileBuffer, filename || 'animation.gif');
    formData.append('channels', channel_id);
    if (title) formData.append('title', title);
    if (comment) formData.append('initial_comment', comment);

    const response = await axios.post(
      'https://slack.com/api/files.upload',
      formData,
      {
        headers: {
          'Authorization': `Bearer ${workspace.access_token}`,
          ...formData.getHeaders()
        }
      }
    );

    if (!response.data.ok) {
      return res.status(400).json({
        error: 'Failed to upload file',
        details: response.data.error
      });
    }

    res.json({
      success: true,
      file: response.data.file
    });

  } catch (err: any) {
    console.error('File upload error:', err);
    res.status(500).json({
      error: 'Failed to upload file to Slack',
      details: err.message
    });
  }
});

/**
 * Get list of channels for a workspace
 */
router.get('/channels/:team_id', async (req: Request, res: Response) => {
  const { team_id } = req.params;

  const workspace = workspaceTokens.get(team_id);
  if (!workspace) {
    return res.status(401).json({
      error: 'Workspace not authenticated'
    });
  }

  try {
    const response = await axios.get(
      'https://slack.com/api/conversations.list',
      {
        headers: {
          'Authorization': `Bearer ${workspace.access_token}`
        },
        params: {
          types: 'public_channel,private_channel'
        }
      }
    );

    if (!response.data.ok) {
      return res.status(400).json({
        error: 'Failed to fetch channels',
        details: response.data.error
      });
    }

    res.json({
      success: true,
      channels: response.data.channels
    });

  } catch (err: any) {
    console.error('Fetch channels error:', err);
    res.status(500).json({
      error: 'Failed to fetch channels',
      details: err.message
    });
  }
});

/**
 * Health check endpoint
 */
router.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'ok',
    service: 'slack-integration',
    configured: !!(SLACK_CLIENT_ID && SLACK_CLIENT_SECRET),
    workspaces: workspaceTokens.size
  });
});

export default router;
