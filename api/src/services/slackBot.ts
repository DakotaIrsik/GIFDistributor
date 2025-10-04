/**
 * Slack Bot Service - OAuth Integration & Message Posting
 * Issue: #26
 *
 * Provides centralized Slack bot functionality including:
 * - OAuth token management
 * - Message posting with hosted GIFs
 * - File uploads
 * - Workspace integration
 */

import axios from 'axios';
import crypto from 'crypto';

export interface SlackWorkspace {
  access_token: string;
  team_id: string;
  team_name: string;
  bot_user_id: string;
  scope: string;
  installed_at: Date;
}

export interface SlackMessage {
  channel: string;
  text?: string;
  gif_url?: string;
  title?: string;
  tags?: string[];
  thread_ts?: string;
}

export interface SlackFileUpload {
  channel: string;
  file_url: string;
  filename?: string;
  title?: string;
  comment?: string;
}

class SlackBotService {
  private workspaces: Map<string, SlackWorkspace> = new Map();
  private clientId: string;
  private clientSecret: string;
  private signingSecret: string;
  private redirectUri: string;

  constructor() {
    this.clientId = process.env.SLACK_CLIENT_ID || '';
    this.clientSecret = process.env.SLACK_CLIENT_SECRET || '';
    this.signingSecret = process.env.SLACK_SIGNING_SECRET || '';
    this.redirectUri = process.env.SLACK_REDIRECT_URI || 'http://localhost:3001/api/slack/oauth/callback';
  }

  /**
   * Generate OAuth installation URL
   */
  generateInstallUrl(state?: string): string {
    const stateParam = state || crypto.randomBytes(16).toString('hex');
    const scopes = [
      'chat:write',
      'files:write',
      'links:write',
      'channels:read',
      'groups:read',
      'im:read',
      'mpim:read'
    ].join(',');

    return `https://slack.com/oauth/v2/authorize?client_id=${this.clientId}&scope=${scopes}&redirect_uri=${encodeURIComponent(this.redirectUri)}&state=${stateParam}`;
  }

  /**
   * Exchange OAuth code for access token
   */
  async exchangeCodeForToken(code: string): Promise<SlackWorkspace> {
    try {
      const response = await axios.post(
        'https://slack.com/api/oauth.v2.access',
        new URLSearchParams({
          client_id: this.clientId,
          client_secret: this.clientSecret,
          code,
          redirect_uri: this.redirectUri
        }).toString(),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        }
      );

      if (!response.data.ok) {
        throw new Error(`OAuth exchange failed: ${response.data.error}`);
      }

      const workspace: SlackWorkspace = {
        access_token: response.data.access_token,
        team_id: response.data.team.id,
        team_name: response.data.team.name,
        bot_user_id: response.data.bot_user_id,
        scope: response.data.scope,
        installed_at: new Date()
      };

      this.workspaces.set(workspace.team_id, workspace);
      return workspace;
    } catch (error: any) {
      throw new Error(`Failed to exchange OAuth code: ${error.message}`);
    }
  }

  /**
   * Post a message with hosted GIF to a Slack channel
   */
  async postMessage(teamId: string, message: SlackMessage): Promise<any> {
    const workspace = this.workspaces.get(teamId);
    if (!workspace) {
      throw new Error('Workspace not authenticated');
    }

    const payload: any = {
      channel: message.channel,
      text: message.text || message.title || 'Check out this GIF!'
    };

    // Add GIF as attachment if provided
    if (message.gif_url) {
      payload.attachments = [
        {
          fallback: message.title || 'GIF from GIF Distributor',
          image_url: message.gif_url,
          title: message.title,
          color: '#FF6B35'
        }
      ];

      // Add tags as footer
      if (message.tags && message.tags.length > 0) {
        payload.attachments[0].footer = `Tags: ${message.tags.join(', ')}`;
      }
    }

    // Support threading
    if (message.thread_ts) {
      payload.thread_ts = message.thread_ts;
    }

    try {
      const response = await axios.post(
        'https://slack.com/api/chat.postMessage',
        payload,
        {
          headers: {
            'Authorization': `Bearer ${workspace.access_token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.data.ok) {
        throw new Error(`Slack API error: ${response.data.error}`);
      }

      return response.data;
    } catch (error: any) {
      throw new Error(`Failed to post message: ${error.message}`);
    }
  }

  /**
   * Upload a file directly to Slack
   */
  async uploadFile(teamId: string, upload: SlackFileUpload): Promise<any> {
    const workspace = this.workspaces.get(teamId);
    if (!workspace) {
      throw new Error('Workspace not authenticated');
    }

    try {
      // Download file from URL
      const fileResponse = await axios.get(upload.file_url, {
        responseType: 'arraybuffer'
      });
      const fileBuffer = Buffer.from(fileResponse.data);

      // Upload to Slack
      const FormData = require('form-data');
      const formData = new FormData();
      formData.append('file', fileBuffer, upload.filename || 'animation.gif');
      formData.append('channels', upload.channel);
      if (upload.title) formData.append('title', upload.title);
      if (upload.comment) formData.append('initial_comment', upload.comment);

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
        throw new Error(`Slack API error: ${response.data.error}`);
      }

      return response.data;
    } catch (error: any) {
      throw new Error(`Failed to upload file: ${error.message}`);
    }
  }

  /**
   * Get list of channels for a workspace
   */
  async getChannels(teamId: string): Promise<any[]> {
    const workspace = this.workspaces.get(teamId);
    if (!workspace) {
      throw new Error('Workspace not authenticated');
    }

    try {
      const response = await axios.get(
        'https://slack.com/api/conversations.list',
        {
          headers: {
            'Authorization': `Bearer ${workspace.access_token}`
          },
          params: {
            types: 'public_channel,private_channel',
            limit: 200
          }
        }
      );

      if (!response.data.ok) {
        throw new Error(`Slack API error: ${response.data.error}`);
      }

      return response.data.channels;
    } catch (error: any) {
      throw new Error(`Failed to fetch channels: ${error.message}`);
    }
  }

  /**
   * Verify Slack request signature for webhook security
   */
  verifySignature(signature: string, timestamp: string, body: string): boolean {
    if (!this.signingSecret) {
      return false;
    }

    const currentTime = Math.floor(Date.now() / 1000);
    const requestTime = parseInt(timestamp);

    // Reject requests older than 5 minutes
    if (Math.abs(currentTime - requestTime) > 300) {
      return false;
    }

    const sigBasestring = `v0:${timestamp}:${body}`;
    const mySignature = 'v0=' + crypto
      .createHmac('sha256', this.signingSecret)
      .update(sigBasestring)
      .digest('hex');

    return crypto.timingSafeEqual(
      Buffer.from(mySignature),
      Buffer.from(signature)
    );
  }

  /**
   * Store workspace token (in production, use database)
   */
  storeWorkspace(workspace: SlackWorkspace): void {
    this.workspaces.set(workspace.team_id, workspace);
  }

  /**
   * Get workspace by team ID
   */
  getWorkspace(teamId: string): SlackWorkspace | undefined {
    return this.workspaces.get(teamId);
  }

  /**
   * Remove workspace (for uninstallation)
   */
  removeWorkspace(teamId: string): boolean {
    return this.workspaces.delete(teamId);
  }

  /**
   * Check if service is properly configured
   */
  isConfigured(): boolean {
    return !!(this.clientId && this.clientSecret && this.signingSecret);
  }

  /**
   * Get service status
   */
  getStatus(): any {
    return {
      configured: this.isConfigured(),
      workspaces: this.workspaces.size,
      client_id: this.clientId ? '***' + this.clientId.slice(-4) : 'not set'
    };
  }
}

// Export singleton instance
export const slackBot = new SlackBotService();
