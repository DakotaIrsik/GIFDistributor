# GIF Distributor Web Application

This is a full-stack web application scaffold for the GIF Distributor platform.

## Architecture

- **Frontend**: Next.js 14 (React 18, TypeScript)
- **Backend**: Node.js + Express (TypeScript)
- **Queue**: Bull (Redis-backed job queue)
- **Containerization**: Docker + Docker Compose

## Structure

```
.
├── web/                 # Next.js frontend
│   ├── src/
│   │   └── app/        # App Router pages
│   ├── package.json
│   └── tsconfig.json
├── api/                 # Express backend
│   ├── src/
│   │   ├── index.ts    # Main server
│   │   ├── routes/     # API routes
│   │   └── services/   # Business logic
│   ├── package.json
│   └── tsconfig.json
└── docker-compose.yml   # Services orchestration
```

## Getting Started

### Prerequisites

- Node.js 20+
- Docker and Docker Compose (optional)
- Redis (or use Docker)

### Installation

#### Option 1: Local Development

1. Install root dependencies:
```bash
npm install
```

2. Install workspace dependencies:
```bash
npm install --workspaces
```

3. Start Redis (if not using Docker):
```bash
redis-server
```

4. Start development servers:
```bash
npm run dev
```

This will start:
- Web app at http://localhost:3000
- API server at http://localhost:3001

#### Option 2: Docker

1. Start all services:
```bash
docker-compose up
```

This will start:
- Redis on port 6379
- API on port 3001
- Web on port 3000

### Environment Variables

Create `.env` files based on the `.env.example` files:

**api/.env**:
```
PORT=3001
NODE_ENV=development
REDIS_URL=redis://localhost:6379
```

**web/.env**:
```
NEXT_PUBLIC_API_URL=http://localhost:3001
API_URL=http://localhost:3001
```

## API Endpoints

### Health Check
- `GET /api/health` - Health status

### Queue Management
- `POST /api/queue/jobs` - Add job to queue
- `GET /api/queue/jobs/:id` - Get job status
- `GET /api/queue/stats` - Get queue statistics

### Example: Add a job

```bash
curl -X POST http://localhost:3001/api/queue/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "transcode",
    "data": {
      "fileId": "abc123",
      "format": "mp4"
    }
  }'
```

## Queue System

The application uses Bull for job queue management with Redis as the backend.

### Supported Job Types

- `transcode` - Media transcoding jobs
- `upload` - File upload jobs
- `distribute` - Distribution to platforms

### Job Configuration

- **Retries**: 3 attempts
- **Backoff**: Exponential (starting at 2s)
- **Cleanup**: Completed jobs are auto-removed

## Scripts

Root level:
- `npm run dev` - Start both web and API in dev mode
- `npm run build` - Build all workspaces
- `npm start` - Start production servers
- `npm test` - Run all tests

Web workspace:
- `npm run dev --workspace=web` - Start Next.js dev server
- `npm run build --workspace=web` - Build Next.js app

API workspace:
- `npm run dev --workspace=api` - Start Express dev server
- `npm run build --workspace=api` - Build TypeScript

## Next Steps

1. Add authentication (OAuth + email)
2. Implement file upload endpoints
3. Create upload UI in frontend
4. Add platform integration modules
5. Implement media transcoding workers
6. Add database (PostgreSQL recommended)
7. Set up monitoring and observability

## Related Modules

This scaffold integrates with existing Python modules:
- `storage_cdn.py` - Object storage and CDN
- `upload.py` - Upload handling
- `slack_share.py` - Slack integration
- `platform_renditions.py` - Platform-specific formats

## Production Deployment

For production:

1. Build applications:
```bash
npm run build
```

2. Set production environment variables
3. Use a process manager (PM2, systemd)
4. Set up reverse proxy (nginx, Cloudflare)
5. Configure Redis persistence
6. Enable monitoring and logging

## License

See main project LICENSE
