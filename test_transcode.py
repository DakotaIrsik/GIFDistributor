"""
Tests for the transcode module
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import subprocess

from transcode import (
    Transcoder,
    TranscodeError,
    OutputFormat,
    get_file_size,
    get_size_reduction,
)


@pytest.fixture
def transcoder():
    """Create a transcoder instance with mocked ffmpeg"""
    with patch("transcode.subprocess.run") as mock_run:
        # Mock successful ffmpeg/ffprobe verification
        mock_run.return_value = Mock(returncode=0)
        return Transcoder()


@pytest.fixture
def temp_gif_file():
    """Create a temporary GIF file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
        # Write some dummy data
        f.write(b"GIF89a" + b"\x00" * 100)
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestTranscoder:
    """Tests for Transcoder class"""

    def test_init_with_default_paths(self):
        """Test transcoder initialization with default paths"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            transcoder = Transcoder()
            assert transcoder.ffmpeg_path == "ffmpeg"
            assert transcoder.ffprobe_path == "ffprobe"

    def test_init_with_custom_paths(self):
        """Test transcoder initialization with custom paths"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            transcoder = Transcoder(
                ffmpeg_path="/usr/bin/ffmpeg", ffprobe_path="/usr/bin/ffprobe"
            )
            assert transcoder.ffmpeg_path == "/usr/bin/ffmpeg"
            assert transcoder.ffprobe_path == "/usr/bin/ffprobe"

    def test_init_ffmpeg_not_found(self):
        """Test that initialization fails when ffmpeg is not found"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("ffmpeg not found")
            with pytest.raises(TranscodeError, match="ffmpeg/ffprobe not found"):
                Transcoder()

    def test_verify_ffmpeg_timeout(self):
        """Test that initialization fails when ffmpeg times out"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)
            with pytest.raises(TranscodeError):
                Transcoder()

    def test_get_media_info_success(self, transcoder):
        """Test successful media info retrieval"""
        mock_info = {
            "format": {"duration": "5.5", "size": "1024000"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "gif",
                    "width": 640,
                    "height": 480,
                }
            ],
        }

        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(mock_info).encode()
            )

            info = transcoder.get_media_info("test.gif")

            assert info["duration"] == 5.5
            assert info["size"] == 1024000
            assert info["width"] == 640
            assert info["height"] == 480
            assert info["codec"] == "gif"

    def test_get_media_info_no_video_stream(self, transcoder):
        """Test media info with no video stream"""
        mock_info = {"format": {"duration": "5.5", "size": "1024000"}, "streams": []}

        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(mock_info).encode()
            )

            info = transcoder.get_media_info("test.gif")

            assert info["width"] == 0
            assert info["height"] == 0
            assert info["codec"] == "unknown"

    def test_get_media_info_ffprobe_error(self, transcoder):
        """Test media info when ffprobe fails"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")

            with pytest.raises(TranscodeError, match="Failed to get media info"):
                transcoder.get_media_info("test.gif")

    def test_get_media_info_invalid_json(self, transcoder):
        """Test media info with invalid JSON response"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b"invalid json")

            with pytest.raises(TranscodeError, match="Failed to parse ffprobe output"):
                transcoder.get_media_info("test.gif")

    def test_transcode_to_mp4_default_output(self, transcoder, temp_gif_file):
        """Test MP4 transcoding with default output path"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            output = transcoder.transcode_to_mp4(temp_gif_file)

            expected_output = str(Path(temp_gif_file).with_suffix(".mp4"))
            assert output == expected_output

            # Verify ffmpeg was called with correct arguments
            call_args = mock_run.call_args[0][0]
            assert "ffmpeg" in call_args[0]
            assert "-i" in call_args
            assert temp_gif_file in call_args
            assert "-movflags" in call_args
            assert "faststart" in call_args
            assert "-vcodec" in call_args
            assert "libx264" in call_args

    def test_transcode_to_mp4_custom_output(self, transcoder, temp_gif_file):
        """Test MP4 transcoding with custom output path"""
        custom_output = "/tmp/custom_output.mp4"

        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            output = transcoder.transcode_to_mp4(temp_gif_file, custom_output)

            assert output == custom_output
            call_args = mock_run.call_args[0][0]
            assert custom_output in call_args

    def test_transcode_to_mp4_quality_settings(self, transcoder, temp_gif_file):
        """Test MP4 transcoding with different quality settings"""
        qualities = ["low", "medium", "high"]

        for quality in qualities:
            with patch("transcode.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                transcoder.transcode_to_mp4(temp_gif_file, quality=quality)

                call_args = mock_run.call_args[0][0]
                assert "-crf" in call_args
                assert "-preset" in call_args

    def test_transcode_to_mp4_with_max_width(self, transcoder, temp_gif_file):
        """Test MP4 transcoding with max width constraint"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            transcoder.transcode_to_mp4(temp_gif_file, max_width=800)

            call_args = mock_run.call_args[0][0]
            assert "-vf" in call_args
            vf_index = call_args.index("-vf")
            assert "scale" in call_args[vf_index + 1]
            assert "800" in call_args[vf_index + 1]

    def test_transcode_to_mp4_ffmpeg_error(self, transcoder, temp_gif_file):
        """Test MP4 transcoding when ffmpeg fails"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")

            with pytest.raises(TranscodeError, match="Failed to transcode to MP4"):
                transcoder.transcode_to_mp4(temp_gif_file)

    def test_transcode_to_webp_default_output(self, transcoder, temp_gif_file):
        """Test WebP transcoding with default output path"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            output = transcoder.transcode_to_webp(temp_gif_file)

            expected_output = str(Path(temp_gif_file).with_suffix(".webp"))
            assert output == expected_output

            call_args = mock_run.call_args[0][0]
            assert "ffmpeg" in call_args[0]
            assert "-i" in call_args
            assert temp_gif_file in call_args

    def test_transcode_to_webp_custom_quality(self, transcoder, temp_gif_file):
        """Test WebP transcoding with custom quality"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            transcoder.transcode_to_webp(temp_gif_file, quality=90)

            call_args = mock_run.call_args[0][0]
            assert "-quality" in call_args
            assert "90" in call_args

    def test_transcode_to_webp_lossless(self, transcoder, temp_gif_file):
        """Test WebP transcoding with lossless compression"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            transcoder.transcode_to_webp(temp_gif_file, lossless=True)

            call_args = mock_run.call_args[0][0]
            assert "-lossless" in call_args
            assert "1" in call_args

    def test_transcode_to_webp_ffmpeg_error(self, transcoder, temp_gif_file):
        """Test WebP transcoding when ffmpeg fails"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")

            with pytest.raises(TranscodeError, match="Failed to transcode to WebP"):
                transcoder.transcode_to_webp(temp_gif_file)

    def test_optimize_gif_default_output(self, transcoder, temp_gif_file):
        """Test GIF optimization with default output path"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            output = transcoder.optimize_gif(temp_gif_file)

            base = Path(temp_gif_file)
            expected_output = str(base.parent / f"{base.stem}_optimized{base.suffix}")
            assert output == expected_output

    def test_optimize_gif_custom_colors(self, transcoder, temp_gif_file):
        """Test GIF optimization with custom color palette"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            transcoder.optimize_gif(temp_gif_file, max_colors=128)

            call_args = mock_run.call_args[0][0]
            assert "-vf" in call_args
            vf_index = call_args.index("-vf")
            assert "palettegen=max_colors=128" in call_args[vf_index + 1]

    def test_optimize_gif_with_max_width(self, transcoder, temp_gif_file):
        """Test GIF optimization with max width constraint"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            transcoder.optimize_gif(temp_gif_file, max_width=600)

            call_args = mock_run.call_args[0][0]
            assert "-vf" in call_args
            vf_index = call_args.index("-vf")
            filter_str = call_args[vf_index + 1]
            assert "scale" in filter_str
            assert "600" in filter_str

    def test_optimize_gif_ffmpeg_error(self, transcoder, temp_gif_file):
        """Test GIF optimization when ffmpeg fails"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")

            with pytest.raises(TranscodeError, match="Failed to optimize GIF"):
                transcoder.optimize_gif(temp_gif_file)

    def test_transcode_all_formats_default_output(self, transcoder, temp_gif_file):
        """Test transcoding to all formats with default output directory"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            results = transcoder.transcode_all_formats(temp_gif_file)

            assert "mp4" in results
            assert "webp" in results
            assert "gif" in results

            # Verify all output files are in the same directory as input
            input_dir = Path(temp_gif_file).parent
            for format_key, output_path in results.items():
                assert Path(output_path).parent == input_dir

    def test_transcode_all_formats_custom_output_dir(self, transcoder, temp_gif_file):
        """Test transcoding to all formats with custom output directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("transcode.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                results = transcoder.transcode_all_formats(
                    temp_gif_file, output_dir=temp_dir
                )

                # Verify all output files are in the custom directory
                for format_key, output_path in results.items():
                    assert Path(output_path).parent == Path(temp_dir)

    def test_transcode_all_formats_creates_output_dir(self, transcoder, temp_gif_file):
        """Test that transcode_all_formats creates output directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = os.path.join(temp_dir, "new_dir")

            with patch("transcode.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                transcoder.transcode_all_formats(
                    temp_gif_file, output_dir=non_existent_dir
                )

                assert os.path.exists(non_existent_dir)

    def test_transcode_all_formats_quality_parameter(self, transcoder, temp_gif_file):
        """Test that quality parameter is passed to MP4 transcoding"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            transcoder.transcode_all_formats(temp_gif_file, quality="low")

            # Check that ffmpeg was called multiple times (once for each format)
            assert mock_run.call_count >= 3

    def test_transcode_all_formats_partial_failure(self, transcoder, temp_gif_file):
        """Test that transcode_all_formats fails if any transcoding fails"""
        with patch("transcode.subprocess.run") as mock_run:
            # First call succeeds (MP4), second fails (WebP)
            mock_run.side_effect = [
                Mock(returncode=0),  # MP4 success
                subprocess.CalledProcessError(1, "ffmpeg"),  # WebP failure
            ]

            with pytest.raises(TranscodeError):
                transcoder.transcode_all_formats(temp_gif_file)


class TestOutputFormat:
    """Tests for OutputFormat enum"""

    def test_output_format_values(self):
        """Test that OutputFormat enum has expected values"""
        assert OutputFormat.MP4.value == "mp4"
        assert OutputFormat.WEBP.value == "webp"
        assert OutputFormat.GIF.value == "gif"


class TestUtilityFunctions:
    """Tests for utility functions"""

    def test_get_file_size(self, temp_gif_file):
        """Test get_file_size function"""
        size = get_file_size(temp_gif_file)
        assert size > 0
        assert isinstance(size, int)

    def test_get_size_reduction_smaller_file(self):
        """Test size reduction calculation when transcoded file is smaller"""
        with tempfile.NamedTemporaryFile(
            delete=False
        ) as f1, tempfile.NamedTemporaryFile(delete=False) as f2:
            # Original: 1000 bytes
            f1.write(b"0" * 1000)
            f1.flush()
            f1_name = f1.name
            # Transcoded: 500 bytes
            f2.write(b"0" * 500)
            f2.flush()
            f2_name = f2.name

        try:
            reduction = get_size_reduction(f1_name, f2_name)
            assert reduction == 50.0  # 50% reduction
        finally:
            os.unlink(f1_name)
            os.unlink(f2_name)

    def test_get_size_reduction_larger_file(self):
        """Test size reduction calculation when transcoded file is larger"""
        with tempfile.NamedTemporaryFile(
            delete=False
        ) as f1, tempfile.NamedTemporaryFile(delete=False) as f2:
            # Original: 500 bytes
            f1.write(b"0" * 500)
            f1.flush()
            f1_name = f1.name
            # Transcoded: 1000 bytes
            f2.write(b"0" * 1000)
            f2.flush()
            f2_name = f2.name

        try:
            reduction = get_size_reduction(f1_name, f2_name)
            assert reduction == -100.0  # 100% increase (negative reduction)
        finally:
            os.unlink(f1_name)
            os.unlink(f2_name)

    def test_get_size_reduction_same_size(self):
        """Test size reduction calculation when files are same size"""
        with tempfile.NamedTemporaryFile(
            delete=False
        ) as f1, tempfile.NamedTemporaryFile(delete=False) as f2:
            f1.write(b"0" * 1000)
            f1.flush()
            f1_name = f1.name
            f2.write(b"0" * 1000)
            f2.flush()
            f2_name = f2.name

        try:
            reduction = get_size_reduction(f1_name, f2_name)
            assert reduction == 0.0
        finally:
            os.unlink(f1_name)
            os.unlink(f2_name)

    def test_get_size_reduction_zero_size_original(self):
        """Test size reduction with zero-size original file"""
        with tempfile.NamedTemporaryFile(
            delete=False
        ) as f1, tempfile.NamedTemporaryFile(delete=False) as f2:
            # Original: 0 bytes
            f1.flush()
            f1_name = f1.name
            # Transcoded: 100 bytes
            f2.write(b"0" * 100)
            f2.flush()
            f2_name = f2.name

        try:
            reduction = get_size_reduction(f1_name, f2_name)
            assert reduction == 0.0  # Should return 0 to avoid division by zero
        finally:
            os.unlink(f1_name)
            os.unlink(f2_name)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_transcode_nonexistent_file(self, transcoder):
        """Test transcoding a non-existent file"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")

            with pytest.raises(TranscodeError):
                transcoder.transcode_to_mp4("nonexistent.gif")

    def test_invalid_quality_parameter(self, transcoder, temp_gif_file):
        """Test that invalid quality falls back to default"""
        with patch("transcode.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Invalid quality should fall back to "high"
            transcoder.transcode_to_mp4(temp_gif_file, quality="invalid")

            call_args = mock_run.call_args[0][0]
            # Should use "high" quality settings
            assert "-crf" in call_args
            crf_index = call_args.index("-crf")
            assert call_args[crf_index + 1] == "18"  # High quality CRF
