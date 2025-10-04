import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { queueRouter } from './routes/queue';
import { healthRouter } from './routes/health';
import discordRouter from './routes/discord';
import { discordBot } from './services/discordBot';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use('/api/health', healthRouter);
app.use('/api/queue', queueRouter);
app.use('/api/discord', discordRouter);

// Root route
app.get('/', (req: Request, res: Response) => {
  res.json({
    name: 'GIF Distributor API',
    version: '1.0.0',
    status: 'running',
  });
});

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: any) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined,
  });
});

// Initialize Discord bot if enabled
discordBot.initialize().catch(err => {
  console.error('Failed to initialize Discord bot:', err);
});

app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  await discordBot.shutdown();
  process.exit(0);
});

export default app;
