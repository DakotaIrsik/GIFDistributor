"""
Comprehensive tests for Frame Sampler Module (Issue #11)
"""

import io
import os
import tempfile
import pytest
from pathlib import Path
from PIL import Image

from frame_sampler import (
    FrameSampler,
    MediaType,
    OutputFormat,
    FrameInfo,
    SamplerResult,
    sample_frames,
    get_frame_count,
)


class TestMediaTypeDetection:
    """Test media type detection"""

    def test_detect_gif_from_extension(self, tmp_path):
        """Should detect GIF from .gif extension"""
        test_file = tmp_path / "test.gif"
        test_file.touch()

        media_type = FrameSampler.detect_media_type(str(test_file))
        assert media_type == MediaType.GIF

    def test_detect_mp4_from_extension(self, tmp_path):
        """Should detect MP4 from .mp4 extension"""
        test_file = tmp_path / "test.mp4"
        test_file.touch()

        media_type = FrameSampler.detect_media_type(str(test_file))
        assert media_type == MediaType.MP4

    def test_detect_mov_as_mp4(self, tmp_path):
        """Should detect .mov as MP4"""
        test_file = tmp_path / "test.mov"
        test_file.touch()

        media_type = FrameSampler.detect_media_type(str(test_file))
        assert media_type == MediaType.MP4

    def test_detect_gif_from_content(self, tmp_path):
        """Should detect GIF from file content"""
        test_file = tmp_path / "noext"
        with open(test_file, "wb") as f:
            f.write(b"GIF89a" + b"\x00" * 100)

        media_type = FrameSampler.detect_media_type(str(test_file))
        assert media_type == MediaType.GIF

    def test_detect_unknown_type(self, tmp_path):
        """Should return UNKNOWN for unsupported files"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("not a media file")

        media_type = FrameSampler.detect_media_type(str(test_file))
        assert media_type == MediaType.UNKNOWN


class TestFrameIndexCalculation:
    """Test evenly-spaced frame index calculation"""

    def test_sample_all_frames(self):
        """Should return all indices when samples >= total"""
        indices = FrameSampler.calculate_frame_indices(10, 15)
        assert indices == list(range(10))

    def test_sample_single_frame(self):
        """Should return first frame for single sample"""
        indices = FrameSampler.calculate_frame_indices(100, 1)
        assert indices == [0]

    def test_sample_two_frames(self):
        """Should return first and last for two samples"""
        indices = FrameSampler.calculate_frame_indices(100, 2)
        assert indices == [0, 99]

    def test_even_spacing_5_from_100(self):
        """Should evenly space 5 frames from 100"""
        indices = FrameSampler.calculate_frame_indices(100, 5)
        # Should be approximately [0, 25, 50, 75, 99]
        assert len(indices) == 5
        assert indices[0] == 0
        assert indices[-1] == 99
        # Check spacing is roughly even
        spacing = [indices[i + 1] - indices[i] for i in range(len(indices) - 1)]
        assert all(abs(s - 25) <= 1 for s in spacing)

    def test_zero_samples(self):
        """Should return empty list for zero samples"""
        indices = FrameSampler.calculate_frame_indices(100, 0)
        assert indices == []

    def test_negative_samples(self):
        """Should return empty list for negative samples"""
        indices = FrameSampler.calculate_frame_indices(100, -5)
        assert indices == []


class TestGIFSampling:
    """Test GIF frame sampling"""

    @pytest.fixture
    def simple_gif(self, tmp_path):
        """Create a simple multi-frame GIF"""
        gif_path = tmp_path / "test.gif"

        # Create 10 frames with different colors
        frames = []
        for i in range(10):
            # Create colored frame
            img = Image.new("RGB", (100, 100), color=(i * 25, i * 25, i * 25))
            frames.append(img)

        # Save as animated GIF
        frames[0].save(
            gif_path, save_all=True, append_images=frames[1:], duration=100, loop=0
        )

        return str(gif_path)

    @pytest.fixture
    def static_gif(self, tmp_path):
        """Create a static single-frame GIF"""
        gif_path = tmp_path / "static.gif"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(gif_path)
        return str(gif_path)

    def test_get_gif_frame_count_animated(self, simple_gif):
        """Should count frames in animated GIF"""
        count = FrameSampler.get_gif_frame_count(simple_gif)
        assert count == 10

    def test_get_gif_frame_count_static(self, static_gif):
        """Should return 1 for static GIF"""
        count = FrameSampler.get_gif_frame_count(static_gif)
        assert count == 1

    def test_sample_gif_pil_format(self, simple_gif):
        """Should sample GIF and return PIL Images"""
        result = FrameSampler.sample_gif(simple_gif, 5, OutputFormat.PIL_IMAGE)

        assert isinstance(result, SamplerResult)
        assert result.media_type == MediaType.GIF
        assert result.total_frames == 10
        assert len(result.frames) == 5
        assert len(result.frame_info) == 5

        # Check frames are PIL Images
        for frame in result.frames:
            assert isinstance(frame, Image.Image)

        # Check frame info
        for info in result.frame_info:
            assert isinstance(info, FrameInfo)
            assert info.width == 100
            assert info.height == 100
            assert info.format == "RGB"

    def test_sample_gif_bytes_format(self, simple_gif):
        """Should sample GIF and return PNG bytes"""
        result = FrameSampler.sample_gif(simple_gif, 3, OutputFormat.BYTES)

        assert len(result.frames) == 3

        # Check frames are bytes
        for frame_bytes in result.frames:
            assert isinstance(frame_bytes, bytes)
            assert frame_bytes.startswith(b"\x89PNG")  # PNG magic number

    def test_sample_gif_file_format(self, simple_gif, tmp_path):
        """Should sample GIF and save to files"""
        output_dir = tmp_path / "output"

        result = FrameSampler.sample_gif(
            simple_gif, 4, OutputFormat.FILE, str(output_dir)
        )

        assert len(result.frames) == 4

        # Check files were created
        for filepath in result.frames:
            assert isinstance(filepath, str)
            assert os.path.exists(filepath)
            assert filepath.endswith(".png")

            # Verify it's a valid image
            with Image.open(filepath) as img:
                assert img.size == (100, 100)

    def test_sample_gif_file_without_output_dir(self, simple_gif):
        """Should raise error if output_dir not provided for FILE format"""
        with pytest.raises(ValueError, match="output_dir required"):
            FrameSampler.sample_gif(simple_gif, 3, OutputFormat.FILE)

    def test_sample_gif_nonexistent_file(self):
        """Should raise FileNotFoundError for missing file"""
        with pytest.raises(FileNotFoundError):
            FrameSampler.sample_gif("nonexistent.gif", 5)

    def test_sample_all_gif_frames(self, simple_gif):
        """Should return all frames when samples >= total"""
        result = FrameSampler.sample_gif(simple_gif, 15, OutputFormat.PIL_IMAGE)

        assert len(result.frames) == 10  # All frames
        assert result.total_frames == 10

    def test_sample_single_gif_frame(self, simple_gif):
        """Should sample single frame"""
        result = FrameSampler.sample_gif(simple_gif, 1, OutputFormat.PIL_IMAGE)

        assert len(result.frames) == 1
        assert result.frame_info[0].index == 0

    def test_static_gif_sampling(self, static_gif):
        """Should handle static GIF correctly"""
        result = FrameSampler.sample_gif(static_gif, 5, OutputFormat.PIL_IMAGE)

        assert len(result.frames) == 1  # Only 1 frame available
        assert result.total_frames == 1


class TestVideoSampling:
    """Test MP4/video frame sampling"""

    @pytest.fixture
    def sample_video(self, tmp_path):
        """Create a sample video using ffmpeg"""
        video_path = tmp_path / "test.mp4"

        # Create a 2-second test video with 30fps (60 frames)
        # Generate color gradient video
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=320x240:rate=30",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(video_path),
        ]

        import subprocess

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("ffmpeg not available")

        return str(video_path)

    def test_get_video_info(self, sample_video):
        """Should get video frame count and duration"""
        frame_count, duration_ms = FrameSampler.get_video_info(sample_video)

        assert frame_count > 0
        assert duration_ms > 0
        # Should be around 2000ms (2 seconds)
        assert 1800 < duration_ms < 2200

    def test_sample_video_pil_format(self, sample_video):
        """Should sample video and return PIL Images"""
        result = FrameSampler.sample_video(sample_video, 5, OutputFormat.PIL_IMAGE)

        assert isinstance(result, SamplerResult)
        assert result.media_type == MediaType.MP4
        assert result.total_frames > 0
        assert result.duration_ms is not None
        assert len(result.frames) == 5
        assert len(result.frame_info) == 5

        # Check frames are PIL Images
        for frame in result.frames:
            assert isinstance(frame, Image.Image)
            assert frame.size == (320, 240)

        # Check frame info has timestamps
        for info in result.frame_info:
            assert info.timestamp_ms is not None
            assert info.timestamp_ms >= 0

    def test_sample_video_bytes_format(self, sample_video):
        """Should sample video and return PNG bytes"""
        result = FrameSampler.sample_video(sample_video, 3, OutputFormat.BYTES)

        assert len(result.frames) == 3

        for frame_bytes in result.frames:
            assert isinstance(frame_bytes, bytes)
            assert frame_bytes.startswith(b"\x89PNG")

    def test_sample_video_file_format(self, sample_video, tmp_path):
        """Should sample video and save to files"""
        output_dir = tmp_path / "video_frames"

        result = FrameSampler.sample_video(
            sample_video, 4, OutputFormat.FILE, str(output_dir)
        )

        assert len(result.frames) == 4

        for filepath in result.frames:
            assert os.path.exists(filepath)
            assert filepath.endswith(".png")

            with Image.open(filepath) as img:
                assert img.size == (320, 240)

    def test_sample_video_nonexistent_file(self):
        """Should raise FileNotFoundError for missing file"""
        with pytest.raises(FileNotFoundError):
            FrameSampler.sample_video("nonexistent.mp4", 5)


class TestUnifiedSampling:
    """Test unified sample_media function"""

    @pytest.fixture
    def test_gif(self, tmp_path):
        """Create test GIF"""
        gif_path = tmp_path / "test.gif"
        frames = [
            Image.new("RGB", (50, 50), color=f"#{i*40:02x}0000") for i in range(5)
        ]
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=100)
        return str(gif_path)

    def test_sample_media_auto_detect_gif(self, test_gif):
        """Should auto-detect and sample GIF"""
        result = FrameSampler.sample_media(test_gif, 3)

        assert result.media_type == MediaType.GIF
        assert len(result.frames) == 3

    def test_sample_media_force_type(self, test_gif):
        """Should use forced media type"""
        result = FrameSampler.sample_media(test_gif, 2, media_type=MediaType.GIF)

        assert result.media_type == MediaType.GIF
        assert len(result.frames) == 2

    def test_sample_media_unsupported_type(self, tmp_path):
        """Should raise error for unsupported media type"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a media file")

        with pytest.raises(ValueError, match="Unsupported media type"):
            FrameSampler.sample_media(str(txt_file), 5)


class TestConvenienceFunctions:
    """Test convenience wrapper functions"""

    @pytest.fixture
    def test_gif(self, tmp_path):
        """Create test GIF"""
        gif_path = tmp_path / "test.gif"
        frames = [Image.new("RGB", (50, 50), color="blue") for _ in range(8)]
        frames[0].save(
            gif_path, save_all=True, append_images=frames[1:], duration=100, loop=0
        )
        return str(gif_path)

    def test_sample_frames_pil(self, tmp_path):
        """Should use sample_frames helper for PIL format"""
        # Create animated GIF
        gif_path = tmp_path / "test.gif"
        frames_list = [
            Image.new("RGB", (50, 50), color=(i * 30, 0, 0)) for i in range(8)
        ]
        frames_list[0].save(
            gif_path, save_all=True, append_images=frames_list[1:], duration=100, loop=0
        )

        frames = sample_frames(str(gif_path), 4, output_format="pil")

        assert len(frames) == 4
        assert all(isinstance(f, Image.Image) for f in frames)

    def test_sample_frames_bytes(self, tmp_path):
        """Should use sample_frames helper for bytes format"""
        # Create animated GIF
        gif_path = tmp_path / "test.gif"
        frames_list = [
            Image.new("RGB", (50, 50), color=(i * 30, 0, 0)) for i in range(8)
        ]
        frames_list[0].save(
            gif_path, save_all=True, append_images=frames_list[1:], duration=100, loop=0
        )

        frames = sample_frames(str(gif_path), 3, output_format="bytes")

        assert len(frames) == 3
        assert all(isinstance(f, bytes) for f in frames)

    def test_get_frame_count_gif(self, tmp_path):
        """Should get frame count using helper"""
        # Create animated GIF
        gif_path = tmp_path / "test.gif"
        frames_list = [
            Image.new("RGB", (50, 50), color=(i * 30, 0, 0)) for i in range(8)
        ]
        frames_list[0].save(
            gif_path, save_all=True, append_images=frames_list[1:], duration=100, loop=0
        )

        count = get_frame_count(str(gif_path))
        assert count == 8

    def test_get_frame_count_unsupported(self, tmp_path):
        """Should raise error for unsupported file"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a media file")

        with pytest.raises(ValueError, match="Unsupported media type"):
            get_frame_count(str(txt_file))


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_large_frame_count_request(self, tmp_path):
        """Should handle requesting more frames than exist"""
        gif_path = tmp_path / "small.gif"
        frames = [Image.new("RGB", (10, 10), color=(i * 80, 0, 0)) for i in range(3)]
        frames[0].save(
            gif_path, save_all=True, append_images=frames[1:], duration=100, loop=0
        )

        result = FrameSampler.sample_gif(str(gif_path), 100)
        assert len(result.frames) == 3  # All available frames

    def test_zero_frame_request(self, tmp_path):
        """Should handle zero frame request"""
        gif_path = tmp_path / "test.gif"
        img = Image.new("RGB", (10, 10), "blue")
        img.save(gif_path)

        result = FrameSampler.sample_gif(str(gif_path), 0)
        assert len(result.frames) == 0
        assert len(result.frame_info) == 0

    def test_corrupted_gif_handling(self, tmp_path):
        """Should handle corrupted GIF gracefully"""
        bad_gif = tmp_path / "corrupted.gif"
        bad_gif.write_bytes(b"GIF89a\x00\x00" + b"\xff" * 100)

        # PIL should raise an error when trying to open corrupted file
        with pytest.raises(Exception):  # Could be various PIL exceptions
            FrameSampler.sample_gif(str(bad_gif), 5)


class TestFrameInfo:
    """Test FrameInfo metadata structure"""

    def test_frame_info_attributes(self, tmp_path):
        """Should populate frame info correctly"""
        gif_path = tmp_path / "test.gif"
        img = Image.new("RGB", (200, 150), "green")
        img.save(gif_path)

        result = FrameSampler.sample_gif(str(gif_path), 1)
        info = result.frame_info[0]

        assert info.index == 0
        assert info.width == 200
        assert info.height == 150
        assert info.format == "RGB"
        assert info.timestamp_ms is None  # GIFs don't have timestamps


class TestOutputDirectories:
    """Test output directory handling"""

    def test_create_output_directory(self, tmp_path):
        """Should create output directory if it doesn't exist"""
        gif_path = tmp_path / "test.gif"
        img = Image.new("RGB", (50, 50), "blue")
        img.save(gif_path)

        output_dir = tmp_path / "new" / "nested" / "dir"

        result = FrameSampler.sample_gif(
            str(gif_path), 1, OutputFormat.FILE, str(output_dir)
        )

        assert output_dir.exists()
        assert os.path.exists(result.frames[0])


class TestIntegration:
    """Integration tests combining multiple features"""

    def test_sample_multiple_formats_same_gif(self, tmp_path):
        """Should sample same GIF in different formats"""
        gif_path = tmp_path / "test.gif"
        frames = [
            Image.new("RGB", (100, 100), color=f"#{i*50:02x}0000") for i in range(6)
        ]
        frames[0].save(gif_path, save_all=True, append_images=frames[1:])

        # Sample as PIL
        result_pil = FrameSampler.sample_gif(str(gif_path), 3, OutputFormat.PIL_IMAGE)

        # Sample as bytes
        result_bytes = FrameSampler.sample_gif(str(gif_path), 3, OutputFormat.BYTES)

        # Sample as files
        output_dir = tmp_path / "frames"
        result_files = FrameSampler.sample_gif(
            str(gif_path), 3, OutputFormat.FILE, str(output_dir)
        )

        # All should have same frame count and indices
        assert (
            len(result_pil.frames)
            == len(result_bytes.frames)
            == len(result_files.frames)
            == 3
        )
        assert [f.index for f in result_pil.frame_info] == [
            f.index for f in result_bytes.frame_info
        ]

    def test_workflow_detect_count_sample(self, tmp_path):
        """Test complete workflow: detect -> count -> sample"""
        # Create test file
        gif_path = tmp_path / "workflow.gif"
        frames_list = [
            Image.new("RGB", (80, 80), color=(i * 20, 0, i * 20)) for i in range(12)
        ]
        frames_list[0].save(
            gif_path, save_all=True, append_images=frames_list[1:], duration=100, loop=0
        )

        # 1. Detect type
        media_type = FrameSampler.detect_media_type(str(gif_path))
        assert media_type == MediaType.GIF

        # 2. Get frame count
        count = get_frame_count(str(gif_path))
        assert count == 12

        # 3. Sample frames
        num_samples = 4
        frames = sample_frames(str(gif_path), num_samples)
        assert len(frames) == num_samples


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
