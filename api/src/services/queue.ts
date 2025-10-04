import Bull, { Queue, Job } from 'bull';
import Redis from 'ioredis';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

// Create Redis client
const redisClient = new Redis(REDIS_URL, {
  maxRetriesPerRequest: null,
  enableReadyCheck: false,
});

// Create Bull queue
const mediaQueue: Queue = new Bull('media-processing', {
  redis: REDIS_URL,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 2000,
    },
    removeOnComplete: true,
    removeOnFail: false,
  },
});

// Job processors
mediaQueue.process('transcode', async (job: Job) => {
  console.log(`Processing transcode job ${job.id}`, job.data);
  // Simulated processing
  await new Promise(resolve => setTimeout(resolve, 1000));
  return { success: true, message: 'Transcode completed' };
});

mediaQueue.process('upload', async (job: Job) => {
  console.log(`Processing upload job ${job.id}`, job.data);
  // Simulated processing
  await new Promise(resolve => setTimeout(resolve, 500));
  return { success: true, message: 'Upload completed' };
});

mediaQueue.process('distribute', async (job: Job) => {
  console.log(`Processing distribute job ${job.id}`, job.data);
  // Simulated processing
  await new Promise(resolve => setTimeout(resolve, 1500));
  return { success: true, message: 'Distribution completed' };
});

// Event handlers
mediaQueue.on('completed', (job: Job, result: any) => {
  console.log(`Job ${job.id} completed with result:`, result);
});

mediaQueue.on('failed', (job: Job, err: Error) => {
  console.error(`Job ${job.id} failed:`, err.message);
});

mediaQueue.on('error', (error: Error) => {
  console.error('Queue error:', error);
});

// Queue service interface
export const queueService = {
  async addJob(type: string, data: any): Promise<Job> {
    return mediaQueue.add(type, data);
  },

  async getJob(id: string): Promise<Job | null> {
    return mediaQueue.getJob(id);
  },

  async getStats() {
    const [waiting, active, completed, failed, delayed] = await Promise.all([
      mediaQueue.getWaitingCount(),
      mediaQueue.getActiveCount(),
      mediaQueue.getCompletedCount(),
      mediaQueue.getFailedCount(),
      mediaQueue.getDelayedCount(),
    ]);

    return {
      waiting,
      active,
      completed,
      failed,
      delayed,
      total: waiting + active + completed + failed + delayed,
    };
  },

  async close() {
    await mediaQueue.close();
    redisClient.disconnect();
  },
};

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, closing queue...');
  await queueService.close();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('SIGINT received, closing queue...');
  await queueService.close();
  process.exit(0);
});
