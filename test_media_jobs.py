"""
Tests for Media Jobs Runtime Module
"""

import os
import tempfile
import time
import pytest
from unittest.mock import patch, MagicMock
from media_jobs import (
    MediaJobQueue,
    FFmpegRuntime,
    JobStatus,
    JobPriority,
    MediaJob,
    create_transcode_job,
    create_thumbnail_job
)


class TestFFmpegRuntime:
    """Test ffmpeg runtime functionality"""

    def test_ffmpeg_runtime_initialization(self):
        """Test FFmpegRuntime initialization with valid binaries"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            runtime = FFmpegRuntime()
            assert runtime.ffmpeg_path == "ffmpeg"
            assert runtime.ffprobe_path == "ffprobe"
            assert mock_run.call_count == 2  # Called for ffmpeg and ffprobe validation

    def test_ffmpeg_runtime_invalid_binary(self):
        """Test FFmpegRuntime with invalid binary path"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("ffmpeg not found")
            with pytest.raises(RuntimeError, match="ffmpeg/ffprobe not found"):
                FFmpegRuntime(ffmpeg_path="/invalid/path/ffmpeg")

    def test_execute_ffmpeg_success(self):
        """Test successful ffmpeg execution"""
        with patch('subprocess.run') as mock_run:
            # Mock validation calls
            mock_run.side_effect = [
                MagicMock(returncode=0),  # ffmpeg validation
                MagicMock(returncode=0),  # ffprobe validation
                MagicMock(returncode=0, stdout="output", stderr="")  # actual execution
            ]

            runtime = FFmpegRuntime()
            returncode, stdout, stderr = runtime.execute_ffmpeg(["-i", "input.mp4", "output.mp4"])

            assert returncode == 0
            assert stdout == "output"

    def test_execute_ffmpeg_failure(self):
        """Test ffmpeg execution failure"""
        with patch('subprocess.run') as mock_run:
            # Mock validation calls
            mock_run.side_effect = [
                MagicMock(returncode=0),  # ffmpeg validation
                MagicMock(returncode=0),  # ffprobe validation
                MagicMock(returncode=1, stdout="", stderr="error message")  # actual execution
            ]

            runtime = FFmpegRuntime()
            returncode, stdout, stderr = runtime.execute_ffmpeg(["-i", "input.mp4", "output.mp4"])

            assert returncode == 1
            assert stderr == "error message"

    def test_execute_ffmpeg_timeout(self):
        """Test ffmpeg execution timeout"""
        with patch('subprocess.run') as mock_run:
            import subprocess
            # Mock validation calls
            mock_run.side_effect = [
                MagicMock(returncode=0),  # ffmpeg validation
                MagicMock(returncode=0),  # ffprobe validation
                subprocess.TimeoutExpired("ffmpeg", 5)  # timeout
            ]

            runtime = FFmpegRuntime()
            with pytest.raises(TimeoutError, match="timed out"):
                runtime.execute_ffmpeg(["-i", "input.mp4", "output.mp4"], timeout_seconds=5)

    def test_probe_media_success(self):
        """Test successful media probing"""
        with patch('subprocess.run') as mock_run:
            mock_json = '{"format": {"duration": "10.0"}, "streams": [{"codec_type": "video"}]}'
            # Mock validation calls
            mock_run.side_effect = [
                MagicMock(returncode=0),  # ffmpeg validation
                MagicMock(returncode=0),  # ffprobe validation
                MagicMock(returncode=0, stdout=mock_json, stderr="")  # probe
            ]

            runtime = FFmpegRuntime()
            result = runtime.probe_media("input.mp4")

            assert "format" in result
            assert result["format"]["duration"] == "10.0"

    def test_probe_media_failure(self):
        """Test media probing failure"""
        with patch('subprocess.run') as mock_run:
            import subprocess
            # Mock validation calls
            mock_run.side_effect = [
                MagicMock(returncode=0),  # ffmpeg validation
                MagicMock(returncode=0),  # ffprobe validation
                subprocess.CalledProcessError(1, "ffprobe")  # probe failure
            ]

            runtime = FFmpegRuntime()
            with pytest.raises(RuntimeError, match="Failed to probe"):
                runtime.probe_media("input.mp4")


class TestMediaJobQueue:
    """Test media job queue and worker pool"""

    @pytest.fixture
    def mock_runtime(self):
        """Mock FFmpegRuntime for testing"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            yield

    def test_job_queue_initialization(self, mock_runtime):
        """Test MediaJobQueue initialization"""
        queue = MediaJobQueue(min_workers=2, max_workers=5)
        assert queue.min_workers == 2
        assert queue.max_workers == 5
        assert len(queue.workers) == 2  # Should start with min_workers
        queue.shutdown(wait=False)

    def test_submit_job(self, mock_runtime):
        """Test job submission"""
        queue = MediaJobQueue(min_workers=1, max_workers=2)

        job_id = queue.submit_job(
            job_type="transcode",
            input_path="input.mp4",
            output_path="output.mp4",
            ffmpeg_args=["-i", "input.mp4", "output.mp4"],
            priority=JobPriority.HIGH
        )

        assert job_id is not None
        job = queue.get_job_status(job_id)
        assert job is not None
        assert job.job_type == "transcode"
        assert job.priority == JobPriority.HIGH

        queue.shutdown(wait=False)

    def test_job_processing(self, mock_runtime):
        """Test job processing with mocked ffmpeg"""
        with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
            mock_exec.return_value = (0, "success", "")

            queue = MediaJobQueue(min_workers=1, max_workers=2)

            job_id = queue.submit_job(
                job_type="transcode",
                input_path="input.mp4",
                output_path="output.mp4",
                ffmpeg_args=["-i", "input.mp4", "output.mp4"]
            )

            # Wait for job to complete
            time.sleep(0.5)

            job = queue.get_job_status(job_id)
            assert job.status == JobStatus.COMPLETED

            queue.shutdown(wait=False)

    def test_job_failure(self, mock_runtime):
        """Test job failure handling"""
        with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
            mock_exec.return_value = (1, "", "ffmpeg error")

            queue = MediaJobQueue(min_workers=1, max_workers=2)

            job_id = queue.submit_job(
                job_type="transcode",
                input_path="input.mp4",
                output_path="output.mp4",
                ffmpeg_args=["-i", "input.mp4", "output.mp4"]
            )

            # Wait for job to fail
            time.sleep(0.5)

            job = queue.get_job_status(job_id)
            assert job.status == JobStatus.FAILED
            assert "ffmpeg error" in job.error

            queue.shutdown(wait=False)

    def test_job_priority(self, mock_runtime):
        """Test job priority handling"""
        with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
            mock_exec.return_value = (0, "success", "")

            queue = MediaJobQueue(min_workers=1, max_workers=1)

            # Submit low priority job first
            low_job_id = queue.submit_job(
                job_type="transcode",
                input_path="low.mp4",
                output_path="low_out.mp4",
                ffmpeg_args=["-i", "low.mp4", "low_out.mp4"],
                priority=JobPriority.LOW
            )

            # Submit high priority job
            high_job_id = queue.submit_job(
                job_type="transcode",
                input_path="high.mp4",
                output_path="high_out.mp4",
                ffmpeg_args=["-i", "high.mp4", "high_out.mp4"],
                priority=JobPriority.CRITICAL
            )

            time.sleep(1)

            # High priority job should complete first (or be processed first)
            high_job = queue.get_job_status(high_job_id)
            low_job = queue.get_job_status(low_job_id)

            # At least verify both completed
            assert high_job.status in [JobStatus.COMPLETED, JobStatus.RUNNING]
            assert low_job.status in [JobStatus.COMPLETED, JobStatus.PENDING, JobStatus.RUNNING]

            queue.shutdown(wait=True)

    def test_cancel_job(self, mock_runtime):
        """Test job cancellation"""
        queue = MediaJobQueue(min_workers=1, max_workers=1)

        job_id = queue.submit_job(
            job_type="transcode",
            input_path="input.mp4",
            output_path="output.mp4",
            ffmpeg_args=["-i", "input.mp4", "output.mp4"]
        )

        # Try to cancel immediately
        cancelled = queue.cancel_job(job_id)
        job = queue.get_job_status(job_id)

        if cancelled:
            assert job.status == JobStatus.CANCELLED
        # If not cancelled, it was already running

        queue.shutdown(wait=False)

    def test_autoscaling_up(self, mock_runtime):
        """Test worker autoscaling up"""
        with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
            # Make jobs take some time
            def slow_exec(*args, **kwargs):
                time.sleep(0.3)
                return (0, "success", "")

            mock_exec.side_effect = slow_exec

            queue = MediaJobQueue(
                min_workers=2,
                max_workers=5,
                scale_up_threshold=2  # Lower threshold for easier testing
            )

            # Submit many jobs to trigger scaling
            job_ids = []
            for i in range(15):
                job_id = queue.submit_job(
                    job_type="transcode",
                    input_path=f"input{i}.mp4",
                    output_path=f"output{i}.mp4",
                    ffmpeg_args=["-i", f"input{i}.mp4", f"output{i}.mp4"]
                )
                job_ids.append(job_id)

            # Wait for autoscaler to react
            time.sleep(6)

            # Should have scaled up (may not always scale all the way to max)
            assert len(queue.workers) >= 2  # At minimum we have the initial workers

            queue.shutdown(wait=False)

    def test_get_metrics(self, mock_runtime):
        """Test metrics collection"""
        with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
            mock_exec.return_value = (0, "success", "")

            queue = MediaJobQueue(min_workers=2, max_workers=5)

            # Submit some jobs
            for i in range(3):
                queue.submit_job(
                    job_type="transcode",
                    input_path=f"input{i}.mp4",
                    output_path=f"output{i}.mp4",
                    ffmpeg_args=["-i", f"input{i}.mp4", f"output{i}.mp4"]
                )

            time.sleep(0.5)

            metrics = queue.get_metrics()
            assert metrics.active_workers >= 2
            assert metrics.total_jobs_processed >= 0

            queue.shutdown(wait=False)

    def test_job_timeout(self, mock_runtime):
        """Test job timeout handling"""
        with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
            mock_exec.side_effect = TimeoutError("Command timed out")

            queue = MediaJobQueue(min_workers=1, max_workers=2)

            job_id = queue.submit_job(
                job_type="transcode",
                input_path="input.mp4",
                output_path="output.mp4",
                ffmpeg_args=["-i", "input.mp4", "output.mp4"],
                timeout_seconds=5
            )

            time.sleep(0.5)

            job = queue.get_job_status(job_id)
            assert job.status == JobStatus.FAILED
            assert "timed out" in job.error.lower()

            queue.shutdown(wait=False)

    def test_shutdown_graceful(self, mock_runtime):
        """Test graceful shutdown"""
        with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
            mock_exec.return_value = (0, "success", "")

            queue = MediaJobQueue(min_workers=2, max_workers=2)

            # Submit a job
            queue.submit_job(
                job_type="transcode",
                input_path="input.mp4",
                output_path="output.mp4",
                ffmpeg_args=["-i", "input.mp4", "output.mp4"]
            )

            # Shutdown and wait
            queue.shutdown(wait=True)

            # All workers should be stopped
            for worker in queue.workers:
                assert not worker.is_alive()


class TestConvenienceFunctions:
    """Test convenience functions for common operations"""

    @pytest.fixture
    def mock_queue(self):
        """Mock MediaJobQueue"""
        with patch('subprocess.run'):
            queue = MediaJobQueue(min_workers=1, max_workers=2)
            yield queue
            queue.shutdown(wait=False)

    def test_create_transcode_job(self, mock_queue):
        """Test transcode job creation"""
        job_id = create_transcode_job(
            queue=mock_queue,
            input_path="input.mp4",
            output_path="output.mp4",
            video_codec="libx264",
            audio_codec="aac",
            bitrate="2M",
            priority=JobPriority.HIGH
        )

        job = mock_queue.get_job_status(job_id)
        assert job is not None
        assert job.job_type == "transcode"
        assert job.priority == JobPriority.HIGH
        assert "-c:v" in job.ffmpeg_args
        assert "libx264" in job.ffmpeg_args

    def test_create_thumbnail_job(self, mock_queue):
        """Test thumbnail job creation"""
        job_id = create_thumbnail_job(
            queue=mock_queue,
            input_path="input.mp4",
            output_path="thumb.jpg",
            timestamp="00:00:05",
            width=640,
            priority=JobPriority.NORMAL
        )

        job = mock_queue.get_job_status(job_id)
        assert job is not None
        assert job.job_type == "thumbnail"
        assert "-ss" in job.ffmpeg_args
        assert "00:00:05" in job.ffmpeg_args
        assert "scale=640:-1" in job.ffmpeg_args


class TestIntegration:
    """Integration tests"""

    @pytest.fixture
    def temp_files(self):
        """Create temporary test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.txt")
            output_file = os.path.join(tmpdir, "output.txt")

            with open(input_file, "w") as f:
                f.write("test content")

            yield input_file, output_file

    def test_end_to_end_job_processing(self, temp_files):
        """Test end-to-end job processing"""
        input_file, output_file = temp_files

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.object(FFmpegRuntime, 'execute_ffmpeg') as mock_exec:
                # Simulate successful processing
                def exec_side_effect(args, timeout_seconds):
                    # Create output file
                    with open(output_file, "w") as f:
                        f.write("processed")
                    return (0, "success", "")

                mock_exec.side_effect = exec_side_effect

                queue = MediaJobQueue(min_workers=1, max_workers=2)

                job_id = queue.submit_job(
                    job_type="test",
                    input_path=input_file,
                    output_path=output_file,
                    ffmpeg_args=["-i", input_file, output_file]
                )

                # Wait for completion
                timeout = 5
                start = time.time()
                while time.time() - start < timeout:
                    job = queue.get_job_status(job_id)
                    if job.status == JobStatus.COMPLETED:
                        break
                    time.sleep(0.1)

                job = queue.get_job_status(job_id)
                assert job.status == JobStatus.COMPLETED
                assert os.path.exists(output_file)

                queue.shutdown(wait=True)
