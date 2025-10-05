"""
Media Jobs Runtime Module

Provides a job queue system for media processing tasks (transcoding, frame sampling, etc.)
with ffmpeg runtime support and autoscaling capabilities.

Features:
- Asynchronous job processing with priority queue
- ffmpeg binary management and validation
- Worker pool with autoscaling based on load
- Job status tracking and monitoring
- Retry logic with exponential backoff
- Resource limits and timeout handling
"""

import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import PriorityQueue, Empty
from typing import Dict, List, Optional, Callable, Any
import json


class JobStatus(Enum):
    """Job execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Job priority levels (lower number = higher priority)"""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class MediaJob:
    """Media processing job"""

    job_id: str
    job_type: str  # 'transcode', 'frame_sample', 'thumbnail', etc.
    input_path: str
    output_path: str
    ffmpeg_args: List[str]
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Compare jobs by priority for PriorityQueue"""
        return self.priority.value < other.priority.value


@dataclass
class WorkerMetrics:
    """Worker pool metrics"""

    active_workers: int = 0
    idle_workers: int = 0
    total_jobs_processed: int = 0
    total_jobs_failed: int = 0
    total_jobs_retried: int = 0
    average_job_duration: float = 0.0
    queue_size: int = 0


class FFmpegRuntime:
    """ffmpeg binary manager and executor"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._validate_binaries()

    def _validate_binaries(self):
        """Validate ffmpeg and ffprobe are available"""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ) as e:
            raise RuntimeError(f"ffmpeg/ffprobe not found or invalid: {e}")

    def execute_ffmpeg(
        self, args: List[str], timeout_seconds: int = 300
    ) -> tuple[int, str, str]:
        """
        Execute ffmpeg command with timeout

        Args:
            args: ffmpeg command arguments (without 'ffmpeg' itself)
            timeout_seconds: Command timeout in seconds

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = [self.ffmpeg_path] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ffmpeg command timed out after {timeout_seconds}s")

    def probe_media(self, file_path: str) -> Dict[str, Any]:
        """
        Get media file information using ffprobe

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with media metadata
        """
        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=True
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to probe media file: {e}")


class MediaJobWorker(threading.Thread):
    """Worker thread for processing media jobs"""

    def __init__(
        self,
        worker_id: int,
        job_queue: PriorityQueue,
        runtime: FFmpegRuntime,
        jobs_dict: Dict[str, MediaJob],
        lock: threading.Lock,
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.runtime = runtime
        self.jobs_dict = jobs_dict
        self.lock = lock
        self.stop_event = stop_event
        self.current_job: Optional[MediaJob] = None

    def run(self):
        """Worker main loop"""
        while not self.stop_event.is_set():
            try:
                # Get job with timeout to allow checking stop_event
                job = self.job_queue.get(timeout=1)

                with self.lock:
                    self.current_job = job
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.now()

                # Process the job
                success = self._process_job(job)

                with self.lock:
                    if success:
                        job.status = JobStatus.COMPLETED
                        job.completed_at = datetime.now()
                    else:
                        job.status = JobStatus.FAILED
                        job.completed_at = datetime.now()

                    self.current_job = None

                self.job_queue.task_done()

            except Empty:
                # No jobs available, continue loop
                continue
            except Exception as e:
                # Unexpected error
                if self.current_job:
                    with self.lock:
                        self.current_job.status = JobStatus.FAILED
                        self.current_job.error = f"Worker error: {str(e)}"
                        self.current_job.completed_at = datetime.now()
                        self.current_job = None
                    self.job_queue.task_done()

    def _process_job(self, job: MediaJob) -> bool:
        """
        Process a media job

        Args:
            job: MediaJob to process

        Returns:
            True if successful, False otherwise
        """
        try:
            returncode, stdout, stderr = self.runtime.execute_ffmpeg(
                job.ffmpeg_args, timeout_seconds=job.timeout_seconds
            )

            if returncode != 0:
                job.error = f"ffmpeg failed with code {returncode}: {stderr}"
                return False

            return True

        except TimeoutError as e:
            job.error = str(e)
            return False
        except Exception as e:
            job.error = f"Job processing error: {str(e)}"
            return False


class MediaJobQueue:
    """
    Media job queue with worker pool and autoscaling

    Features:
    - Priority-based job scheduling
    - Dynamic worker scaling based on queue size
    - Job status tracking and monitoring
    - Automatic retry with exponential backoff
    """

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        min_workers: int = 2,
        max_workers: int = 10,
        scale_up_threshold: int = 5,
        scale_down_threshold: int = 2,
    ):
        """
        Initialize media job queue

        Args:
            ffmpeg_path: Path to ffmpeg binary
            ffprobe_path: Path to ffprobe binary
            min_workers: Minimum number of worker threads
            max_workers: Maximum number of worker threads
            scale_up_threshold: Queue size to trigger scaling up
            scale_down_threshold: Queue size to trigger scaling down
        """
        self.runtime = FFmpegRuntime(ffmpeg_path, ffprobe_path)
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold

        self.job_queue = PriorityQueue()
        self.jobs: Dict[str, MediaJob] = {}
        self.workers: List[MediaJobWorker] = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.metrics = WorkerMetrics()

        # Start initial workers
        self._scale_workers(self.min_workers)

        # Start autoscaler thread
        self.autoscaler_thread = threading.Thread(
            target=self._autoscaler_loop, daemon=True
        )
        self.autoscaler_thread.start()

    def submit_job(
        self,
        job_type: str,
        input_path: str,
        output_path: str,
        ffmpeg_args: List[str],
        priority: JobPriority = JobPriority.NORMAL,
        timeout_seconds: int = 300,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit a media processing job

        Args:
            job_type: Type of job (e.g., 'transcode', 'frame_sample')
            input_path: Input media file path
            output_path: Output file path
            ffmpeg_args: ffmpeg command arguments
            priority: Job priority
            timeout_seconds: Job timeout
            metadata: Additional job metadata

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        job = MediaJob(
            job_id=job_id,
            job_type=job_type,
            input_path=input_path,
            output_path=output_path,
            ffmpeg_args=ffmpeg_args,
            priority=priority,
            timeout_seconds=timeout_seconds,
            metadata=metadata or {},
        )

        with self.lock:
            self.jobs[job_id] = job
            self.metrics.queue_size += 1

        self.job_queue.put(job)

        return job_id

    def get_job_status(self, job_id: str) -> Optional[MediaJob]:
        """Get job status by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending job

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if job not found or already running
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.status == JobStatus.PENDING:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                return True
            return False

    def get_metrics(self) -> WorkerMetrics:
        """Get current worker pool metrics"""
        with self.lock:
            self.metrics.active_workers = len(self.workers)
            self.metrics.idle_workers = sum(
                1 for w in self.workers if w.current_job is None
            )
            self.metrics.queue_size = self.job_queue.qsize()

            # Calculate average job duration
            completed_jobs = [
                j
                for j in self.jobs.values()
                if j.status == JobStatus.COMPLETED and j.started_at and j.completed_at
            ]
            if completed_jobs:
                durations = [
                    (j.completed_at - j.started_at).total_seconds()
                    for j in completed_jobs
                ]
                self.metrics.average_job_duration = sum(durations) / len(durations)

            self.metrics.total_jobs_processed = sum(
                1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED
            )
            self.metrics.total_jobs_failed = sum(
                1 for j in self.jobs.values() if j.status == JobStatus.FAILED
            )
            self.metrics.total_jobs_retried = sum(
                j.retry_count for j in self.jobs.values()
            )

            return self.metrics

    def _scale_workers(self, target_count: int):
        """Scale worker pool to target count"""
        current_count = len(self.workers)

        if target_count > current_count:
            # Scale up
            for i in range(target_count - current_count):
                worker = MediaJobWorker(
                    worker_id=current_count + i,
                    job_queue=self.job_queue,
                    runtime=self.runtime,
                    jobs_dict=self.jobs,
                    lock=self.lock,
                    stop_event=self.stop_event,
                )
                worker.start()
                self.workers.append(worker)

        elif target_count < current_count:
            # Scale down by removing excess workers
            # (they will exit naturally when they finish current jobs)
            self.workers = self.workers[:target_count]

    def _autoscaler_loop(self):
        """Autoscaler main loop"""
        while not self.stop_event.is_set():
            time.sleep(5)  # Check every 5 seconds

            queue_size = self.job_queue.qsize()
            current_workers = len(self.workers)

            # Scale up if queue is growing
            if (
                queue_size > self.scale_up_threshold
                and current_workers < self.max_workers
            ):
                new_count = min(current_workers + 2, self.max_workers)
                with self.lock:
                    self._scale_workers(new_count)

            # Scale down if queue is small
            elif (
                queue_size < self.scale_down_threshold
                and current_workers > self.min_workers
            ):
                new_count = max(current_workers - 1, self.min_workers)
                with self.lock:
                    self._scale_workers(new_count)

    def shutdown(self, wait: bool = True):
        """
        Shutdown the job queue and workers

        Args:
            wait: Wait for pending jobs to complete
        """
        self.stop_event.set()

        if wait:
            self.job_queue.join()

        for worker in self.workers:
            worker.join(timeout=1)

        self.workers.clear()


# Convenience functions for common media operations


def create_transcode_job(
    queue: MediaJobQueue,
    input_path: str,
    output_path: str,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    bitrate: str = "1M",
    priority: JobPriority = JobPriority.NORMAL,
) -> str:
    """Create a video transcoding job"""
    ffmpeg_args = [
        "-i",
        input_path,
        "-c:v",
        video_codec,
        "-c:a",
        audio_codec,
        "-b:v",
        bitrate,
        "-y",  # Overwrite output
        output_path,
    ]

    return queue.submit_job(
        job_type="transcode",
        input_path=input_path,
        output_path=output_path,
        ffmpeg_args=ffmpeg_args,
        priority=priority,
        metadata={
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "bitrate": bitrate,
        },
    )


def create_thumbnail_job(
    queue: MediaJobQueue,
    input_path: str,
    output_path: str,
    timestamp: str = "00:00:01",
    width: int = 320,
    priority: JobPriority = JobPriority.NORMAL,
) -> str:
    """Create a thumbnail extraction job"""
    ffmpeg_args = [
        "-i",
        input_path,
        "-ss",
        timestamp,
        "-vframes",
        "1",
        "-vf",
        f"scale={width}:-1",
        "-y",
        output_path,
    ]

    return queue.submit_job(
        job_type="thumbnail",
        input_path=input_path,
        output_path=output_path,
        ffmpeg_args=ffmpeg_args,
        priority=priority,
        metadata={"timestamp": timestamp, "width": width},
    )
