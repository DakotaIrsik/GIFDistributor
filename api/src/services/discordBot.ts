/**
 * Discord Bot Service for Curated Channel Posting
 *
 * This is an OPTIONAL module for Discord integration.
 * Enables posting curated GIFs to Discord channels with webhooks.
 *
 * Issue #46: Discord bot (optional): curated channel posting
 */

import { Client, GatewayIntentBits, TextChannel, EmbedBuilder } from 'discord.js';

export interface DiscordPostOptions {
  channelId: string;
  title: string;
  description?: string;
  imageUrl: string;
  sourceUrl?: string;
  footer?: string;
}

export interface DiscordWebhookOptions {
  webhookUrl: string;
  username?: string;
  avatarUrl?: string;
  content?: string;
  embeds?: Array<{
    title?: string;
    description?: string;
    image?: { url: string };
    url?: string;
    color?: number;
    footer?: { text: string };
  }>;
}

class DiscordBotService {
  private client: Client | null = null;
  private isEnabled: boolean = false;

  constructor() {
    this.isEnabled = !!process.env.DISCORD_BOT_TOKEN;
  }

  /**
   * Initialize the Discord bot client
   */
  async initialize(): Promise<void> {
    if (!this.isEnabled) {
      console.log('Discord bot is disabled (DISCORD_BOT_TOKEN not set)');
      return;
    }

    this.client = new Client({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
      ],
    });

    this.client.on('ready', () => {
      console.log(`Discord bot logged in as ${this.client?.user?.tag}`);
    });

    this.client.on('error', (error) => {
      console.error('Discord bot error:', error);
    });

    try {
      await this.client.login(process.env.DISCORD_BOT_TOKEN);
    } catch (error) {
      console.error('Failed to initialize Discord bot:', error);
      this.isEnabled = false;
    }
  }

  /**
   * Post a curated GIF to a Discord channel using the bot
   */
  async postToChannel(options: DiscordPostOptions): Promise<boolean> {
    if (!this.isEnabled || !this.client) {
      console.warn('Discord bot is not enabled or initialized');
      return false;
    }

    try {
      const channel = await this.client.channels.fetch(options.channelId);

      if (!channel || !(channel instanceof TextChannel)) {
        console.error('Invalid channel or channel is not a text channel');
        return false;
      }

      const embed = new EmbedBuilder()
        .setTitle(options.title)
        .setImage(options.imageUrl)
        .setColor(0x5865F2); // Discord blurple

      if (options.description) {
        embed.setDescription(options.description);
      }

      if (options.sourceUrl) {
        embed.setURL(options.sourceUrl);
      }

      if (options.footer) {
        embed.setFooter({ text: options.footer });
      }

      await channel.send({ embeds: [embed] });
      return true;
    } catch (error) {
      console.error('Failed to post to Discord channel:', error);
      return false;
    }
  }

  /**
   * Post using a Discord webhook (alternative to bot approach)
   * This is useful for server-specific integrations without requiring bot presence
   */
  async postViaWebhook(options: DiscordWebhookOptions): Promise<boolean> {
    try {
      const response = await fetch(options.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: options.username || 'GIF Distributor',
          avatar_url: options.avatarUrl,
          content: options.content,
          embeds: options.embeds,
        }),
      });

      if (!response.ok) {
        console.error('Webhook post failed:', response.statusText);
        return false;
      }

      return true;
    } catch (error) {
      console.error('Failed to post via Discord webhook:', error);
      return false;
    }
  }

  /**
   * Shutdown the Discord bot client
   */
  async shutdown(): Promise<void> {
    if (this.client) {
      await this.client.destroy();
      this.client = null;
    }
  }

  /**
   * Check if the Discord bot is enabled
   */
  isActive(): boolean {
    return this.isEnabled && this.client !== null && this.client.isReady();
  }
}

// Export singleton instance
export const discordBot = new DiscordBotService();
