/**
 * Discord API Routes
 *
 * Endpoints for posting curated GIFs to Discord channels
 * Issue #46: Discord bot (optional): curated channel posting
 */

import { Router, Request, Response } from 'express';
import { discordBot } from '../services/discordBot';

const router = Router();

/**
 * POST /api/discord/post
 * Post a GIF to a Discord channel using the bot
 */
router.post('/post', async (req: Request, res: Response) => {
  try {
    const { channelId, title, description, imageUrl, sourceUrl, footer } = req.body;

    if (!channelId || !title || !imageUrl) {
      return res.status(400).json({
        error: 'Missing required fields: channelId, title, imageUrl',
      });
    }

    if (!discordBot.isActive()) {
      return res.status(503).json({
        error: 'Discord bot is not active. Check DISCORD_BOT_TOKEN configuration.',
      });
    }

    const success = await discordBot.postToChannel({
      channelId,
      title,
      description,
      imageUrl,
      sourceUrl,
      footer,
    });

    if (success) {
      res.json({ success: true, message: 'Posted to Discord channel' });
    } else {
      res.status(500).json({ error: 'Failed to post to Discord channel' });
    }
  } catch (error) {
    console.error('Discord post error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * POST /api/discord/webhook
 * Post a GIF via Discord webhook (alternative to bot)
 */
router.post('/webhook', async (req: Request, res: Response) => {
  try {
    const { webhookUrl, username, avatarUrl, content, embeds } = req.body;

    if (!webhookUrl) {
      return res.status(400).json({
        error: 'Missing required field: webhookUrl',
      });
    }

    const success = await discordBot.postViaWebhook({
      webhookUrl,
      username,
      avatarUrl,
      content,
      embeds,
    });

    if (success) {
      res.json({ success: true, message: 'Posted via Discord webhook' });
    } else {
      res.status(500).json({ error: 'Failed to post via Discord webhook' });
    }
  } catch (error) {
    console.error('Discord webhook error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * GET /api/discord/status
 * Check Discord bot status
 */
router.get('/status', (req: Request, res: Response) => {
  const isActive = discordBot.isActive();
  res.json({
    active: isActive,
    message: isActive
      ? 'Discord bot is active'
      : 'Discord bot is not configured or inactive',
  });
});

export default router;
