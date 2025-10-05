import { Router, Request, Response } from 'express';
import { queueService } from '../services/queue';

const router = Router();

// Add job to queue
router.post('/jobs', async (req: Request, res: Response) => {
  try {
    const { type, data } = req.body;

    if (!type) {
      return res.status(400).json({ error: 'Job type is required' });
    }

    const job = await queueService.addJob(type, data || {});

    res.status(201).json({
      id: job.id,
      type,
      status: 'queued',
    });
  } catch (error) {
    console.error('Error adding job to queue:', error);
    res.status(500).json({ error: 'Failed to add job to queue' });
  }
});

// Get job status
router.get('/jobs/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const job = await queueService.getJob(id);

    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    const state = await job.getState();

    res.json({
      id: job.id,
      status: state,
      progress: job.progress(),
      data: job.data,
      returnvalue: job.returnvalue,
    });
  } catch (error) {
    console.error('Error getting job:', error);
    res.status(500).json({ error: 'Failed to get job status' });
  }
});

// Get queue stats
router.get('/stats', async (req: Request, res: Response) => {
  try {
    const stats = await queueService.getStats();
    res.json(stats);
  } catch (error) {
    console.error('Error getting queue stats:', error);
    res.status(500).json({ error: 'Failed to get queue stats' });
  }
});

export { router as queueRouter };
