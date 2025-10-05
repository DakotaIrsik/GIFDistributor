# Self-Hosted Runner Setup

This project uses self-hosted GitHub Actions runners to avoid GitHub Actions minutes limits.

## Setup Instructions

### 1. Prepare Runner Machine

Ensure the runner machine has:
- Docker installed (for containerized builds)
- Node.js 20+ (for JavaScript/TypeScript projects)
- Git
- Sufficient disk space for builds and caches

### 2. Register Self-Hosted Runner

1. Go to your GitHub repository → Settings → Actions → Runners
2. Click "New self-hosted runner"
3. Follow the platform-specific instructions to download and configure the runner
4. Run the configuration command:
   ```bash
   ./config.sh --url https://github.com/YOUR_ORG/GIFDistributor --token YOUR_TOKEN
   ```
5. Install as a service:
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

### 3. Runner Labels

Add appropriate labels during configuration:
- `self-hosted` (automatically added)
- `linux` or `windows` or `macos` (based on OS)
- Custom labels as needed (e.g., `gpu`, `high-memory`)

### 4. Security Considerations

- Run the runner in a secure environment
- Use least-privilege service accounts
- Regularly update the runner software
- Monitor runner logs for suspicious activity
- Consider using ephemeral runners for untrusted code

### 5. Maintenance

- Update runner: `./svc.sh stop && ./run.sh --once` (downloads updates automatically)
- Check status: `./svc.sh status`
- View logs: Check runner logs in `_diag/` directory

## Migration Checklist

- [x] Created workflow using `runs-on: self-hosted`
- [ ] Set up at least one self-hosted runner
- [ ] Test workflow execution
- [ ] Monitor resource usage
- [ ] Document runner maintenance procedures
- [ ] Set up backup runners for redundancy
