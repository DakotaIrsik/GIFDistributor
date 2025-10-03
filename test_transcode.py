"""
Tests for Transcode Module - Issue #30
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import subprocess
import json

from transcode import (
    Platform,
    OutputFormat,
    PlatformSpec,
    PLATFORM_SPECS,
    TranscodeOptions,
    TranscodeResult,
    MediaInfo,
    Transcoder,
    RenditionGenerator,
    transcode_to_mp4,
    transcode_to_webp,
    transcode_to_gif,
    generate_platform_renditions,
)


class TestPlatformSpecs:
    """Test platform specifications"""

    def test_all_platforms_have_specs(self):
        """Verify all platforms have specifications"""
        for platform in Platform:
            assert platform in PLATFORM_SPECS
            spec = PLATFORM_SPECS[platform]
            assert spec.name == platform
            assert spec.max_width > 0
            assert spec.max_height > 0
            assert spec.max_filesize_mb > 0
            assert len(spec.preferred_formats) > 0

    def test_giphy_specs(self):
        """Test GIPHY platform specs"""
        spec = PLATFORM_SPECS[Platform.GIPHY]
        assert spec.max_width == 1920
        assert spec.max_height == 1080
        assert spec.max_filesize_mb == 100.0
        assert spec.max_duration_sec == 60.0
        assert OutputFormat.GIF in spec.preferred_formats
        assert spec.max_fps == 30

    def test_tenor_specs(self):
        """Test Tenor platform specs"""
        spec = PLATFORM_SPECS[Platform.TENOR]
        assert spec.max_width == 1920
        assert spec.max_duration_sec == 30.0
        assert OutputFormat.MP4 in spec.preferred_formats

    def test_slack_specs(self):
        """Test Slack platform specs"""
        spec = PLATFORM_SPECS[Platform.SLACK]
        assert spec.max_filesize_mb == 25.0
        assert OutputFormat.WEBP in spec.preferred_formats

    def test_mobile_specs_smaller(self):
        """Mobile should have more restrictive specs"""
        mobile = PLATFORM_SPECS[Platform.MOBILE]
        web = PLATFORM_SPECS[Platform.WEB]
        assert mobile.max_filesize_mb < web.max_filesize_mb
        assert mobile.max_width < web.max_width


class TestMediaInfo:
    """Test MediaInfo helper class"""

    def test_calculate_dimensions_preserve_aspect(self):
        """Test dimension calculation with aspect ratio preservation"""
        # 16:9 video
        width, height = MediaInfo.calculate_dimensions(
            input_width=1920,
            input_height=1080,
            target_width=1280,
            target_height=720,
            preserve_aspect_ratio=True
        )
        assert width == 1280
        assert height == 720

    def test_calculate_dimensions_downscale_width(self):
        """Test downscaling by width only"""
        width, height = MediaInfo.calculate_dimensions(
            input_width=1920,
            input_height=1080,
            target_width=960,
            preserve_aspect_ratio=True
        )
        assert width == 960
        assert height == 540

    def test_calculate_dimensions_max_constraints(self):
        """Test max width/height constraints"""
        width, height = MediaInfo.calculate_dimensions(
            input_width=3840,
            input_height=2160,
            max_width=1920,
            max_height=1080,
            preserve_aspect_ratio=True
        )
        assert width == 1920
        assert height == 1080

    def test_calculate_dimensions_even_numbers(self):
        """Dimensions should be even (codec requirement)"""
        width, height = MediaInfo.calculate_dimensions(
            input_width=1921,
            input_height=1081,
            preserve_aspect_ratio=True
        )
        assert width % 2 == 0
        assert height % 2 == 0

    def test_calculate_dimensions_portrait(self):
        """Test portrait orientation"""
        width, height = MediaInfo.calculate_dimensions(
            input_width=1080,
            input_height=1920,
            max_width=720,
            preserve_aspect_ratio=True
        )
        assert width == 720
        assert height == 1280

    def test_calculate_dimensions_no_preserve_aspect(self):
        """Test without preserving aspect ratio"""
        width, height = MediaInfo.calculate_dimensions(
            input_width=1920,
            input_height=1080,
            target_width=800,
            target_height=800,
            preserve_aspect_ratio=False
        )
        assert width == 800
        assert height == 800

    @patch('subprocess.run')
    def test_get_info_success(self, mock_run):
        """Test successful media info extraction"""
        mock_stdout = json.dumps({
            'streams': [{
                'codec_type': 'video',
                'codec_name': 'h264',
                'width': 1920,
                'height': 1080,
                'r_frame_rate': '30/1'
            }],
            'format': {
                'duration': '10.5',
                'size': '5242880',
                'bit_rate': '4194304',
                'format_name': 'mp4'
            }
        })

        mock_run.return_value = MagicMock(
            stdout=mock_stdout,
            returncode=0
        )

        info = MediaInfo.get_info('/fake/path.mp4')

        assert info['width'] == 1920
        assert info['height'] == 1080
        assert info['codec'] == 'h264'
        assert info['duration'] == 10.5
        assert info['fps'] == 30.0

    @patch('subprocess.run')
    def test_get_info_no_video_stream(self, mock_run):
        """Test handling of files with no video stream"""
        mock_stdout = json.dumps({
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'aac'
            }],
            'format': {}
        })

        mock_run.return_value = MagicMock(
            stdout=mock_stdout,
            returncode=0
        )

        info = MediaInfo.get_info('/fake/path.mp3')
        assert 'error' in info

    @patch('subprocess.run')
    def test_get_info_ffprobe_error(self, mock_run):
        """Test handling ffprobe errors"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')
        info = MediaInfo.get_info('/fake/path.mp4')
        assert 'error' in info


class TestTranscodeOptions:
    """Test TranscodeOptions dataclass"""

    def test_default_options(self):
        """Test default option values"""
        opts = TranscodeOptions(output_format=OutputFormat.MP4)
        assert opts.output_format == OutputFormat.MP4
        assert opts.quality == 85
        assert opts.optimize is True
        assert opts.preserve_aspect_ratio is True

    def test_custom_options(self):
        """Test custom option values"""
        opts = TranscodeOptions(
            output_format=OutputFormat.GIF,
            width=640,
            height=480,
            quality=90,
            fps=24,
            bitrate="1M",
            optimize=False
        )
        assert opts.width == 640
        assert opts.height == 480
        assert opts.quality == 90
        assert opts.fps == 24
        assert opts.bitrate == "1M"


class TestTranscoder:
    """Test Transcoder class"""

    @patch('subprocess.run')
    def test_init_checks_ffmpeg(self, mock_run):
        """Test initialization checks for ffmpeg"""
        mock_run.return_value = MagicMock(returncode=0)
        transcoder = Transcoder()
        assert transcoder.ffmpeg_path == 'ffmpeg'

    @patch('subprocess.run')
    def test_init_ffmpeg_not_found(self, mock_run):
        """Test error when ffmpeg not found"""
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            Transcoder()

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_transcode_input_not_found(self, mock_size, mock_exists, mock_run):
        """Test error when input file doesn't exist"""
        mock_run.return_value = MagicMock(returncode=0)  # ffmpeg check
        mock_exists.return_value = False

        transcoder = Transcoder()
        result = transcoder.transcode(
            '/fake/input.mp4',
            '/fake/output.mp4',
            TranscodeOptions(output_format=OutputFormat.MP4)
        )

        assert result.success is False
        assert 'not found' in result.error.lower()

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_transcode_ffprobe_error(self, mock_exists, mock_run):
        """Test error when ffprobe fails to read input"""
        # First call: ffmpeg version check (success)
        # Second call: ffprobe (fail)
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg check
            subprocess.CalledProcessError(1, 'ffprobe', stderr=b'Invalid file')
        ]
        mock_exists.return_value = True

        transcoder = Transcoder()
        result = transcoder.transcode(
            '/fake/input.mp4',
            '/fake/output.mp4',
            TranscodeOptions(output_format=OutputFormat.MP4)
        )

        assert result.success is False
        assert 'failed' in result.error.lower()

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_transcode_to_mp4_success(self, mock_size, mock_exists, mock_run):
        """Test successful MP4 transcoding"""
        # Mock ffmpeg check
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg version check
            # ffprobe call for input
            MagicMock(
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'r_frame_rate': '30/1'}],
                    'format': {'duration': '10', 'size': '1000000', 'bit_rate': '800000'}
                }),
                returncode=0
            ),
            MagicMock(returncode=0),  # ffmpeg transcode
            # ffprobe call for output
            MagicMock(
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 1280, 'height': 720, 'r_frame_rate': '30/1'}],
                    'format': {'duration': '10', 'size': '500000', 'bit_rate': '400000'}
                }),
                returncode=0
            ),
        ]

        mock_exists.return_value = True
        mock_size.return_value = 500000

        transcoder = Transcoder()
        result = transcoder.transcode(
            '/fake/input.mp4',
            '/fake/output.mp4',
            TranscodeOptions(
                output_format=OutputFormat.MP4,
                width=1280,
                height=720
            )
        )

        assert result.success is True
        assert result.output_format == OutputFormat.MP4
        assert result.output_size_bytes == 500000

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_transcode_to_webp(self, mock_size, mock_exists, mock_run):
        """Test WebP transcoding"""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg check
            MagicMock(  # ffprobe input
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'r_frame_rate': '24/1'}],
                    'format': {'duration': '5', 'size': '1000000', 'bit_rate': '800000'}
                }),
                returncode=0
            ),
            MagicMock(returncode=0),  # ffmpeg transcode
            MagicMock(  # ffprobe output
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 800, 'height': 450, 'r_frame_rate': '24/1'}],
                    'format': {'duration': '5', 'size': '300000', 'bit_rate': '240000'}
                }),
                returncode=0
            ),
        ]

        mock_exists.return_value = True
        mock_size.return_value = 300000

        transcoder = Transcoder()
        result = transcoder.transcode(
            '/fake/input.gif',
            '/fake/output.webp',
            TranscodeOptions(output_format=OutputFormat.WEBP, width=800)
        )

        assert result.success is True
        assert result.output_format == OutputFormat.WEBP

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('os.remove')
    def test_transcode_to_gif_optimized(self, mock_remove, mock_size, mock_exists, mock_run):
        """Test optimized GIF transcoding with palette generation"""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg check
            MagicMock(  # ffprobe input
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'r_frame_rate': '30/1'}],
                    'format': {'duration': '3', 'size': '1000000', 'bit_rate': '800000'}
                }),
                returncode=0
            ),
            MagicMock(returncode=0),  # palette generation
            MagicMock(returncode=0),  # gif creation
            MagicMock(  # ffprobe output
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 640, 'height': 360, 'r_frame_rate': '15/1'}],
                    'format': {'duration': '3', 'size': '400000', 'bit_rate': '320000'}
                }),
                returncode=0
            ),
        ]

        mock_exists.return_value = True
        mock_size.return_value = 400000

        transcoder = Transcoder()
        result = transcoder.transcode(
            '/fake/input.mp4',
            '/fake/output.gif',
            TranscodeOptions(
                output_format=OutputFormat.GIF,
                width=640,
                fps=15,
                optimize=True
            )
        )

        assert result.success is True
        assert result.output_format == OutputFormat.GIF
        # Should have called ffmpeg 3 times (palette + gif + metadata)
        assert mock_run.call_count >= 4


class TestRenditionGenerator:
    """Test RenditionGenerator class"""

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('os.makedirs')
    def test_generate_renditions_single_platform(
        self, mock_makedirs, mock_size, mock_exists, mock_run
    ):
        """Test generating renditions for a single platform"""
        # Mock all subprocess calls
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg version check
        ] + [
            # For each format: ffprobe input, transcode, ffprobe output
            MagicMock(
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'r_frame_rate': '30/1'}],
                    'format': {'duration': '10', 'size': '1000000', 'bit_rate': '800000'}
                }),
                returncode=0
            ),
            MagicMock(returncode=0),
            MagicMock(
                stdout=json.dumps({
                    'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'r_frame_rate': '30/1'}],
                    'format': {'duration': '10', 'size': '800000', 'bit_rate': '640000'}
                }),
                returncode=0
            ),
        ] * 5  # Repeat for multiple formats

        mock_exists.return_value = True
        mock_size.return_value = 800000

        generator = RenditionGenerator()
        results = generator.generate_renditions(
            input_path='/fake/input.mp4',
            output_dir='/fake/output',
            platforms=[Platform.SLACK],
            base_filename='test'
        )

        assert Platform.SLACK in results
        assert len(results[Platform.SLACK]) > 0
        mock_makedirs.assert_called_once_with('/fake/output', exist_ok=True)

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('os.makedirs')
    @patch('os.remove')
    def test_generate_all_platforms(
        self, mock_remove, mock_makedirs, mock_size, mock_exists, mock_run
    ):
        """Test generating renditions for all platforms"""
        # Create enough mocked responses for all platforms and formats
        base_response = [MagicMock(returncode=0)]  # ffmpeg check

        input_probe = MagicMock(
            stdout=json.dumps({
                'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'r_frame_rate': '30/1'}],
                'format': {'duration': '10', 'size': '1000000', 'bit_rate': '800000'}
            }),
            returncode=0
        )

        output_probe = MagicMock(
            stdout=json.dumps({
                'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'r_frame_rate': '30/1'}],
                'format': {'duration': '10', 'size': '500000', 'bit_rate': '400000'}
            }),
            returncode=0
        )

        transcode = MagicMock(returncode=0)

        # Each platform/format combo needs: input_probe, transcode, output_probe
        # Some GIF formats might need extra calls for palette
        mock_run.side_effect = base_response + ([input_probe, transcode, transcode, output_probe] * 30)

        mock_exists.return_value = True
        mock_size.return_value = 500000

        generator = RenditionGenerator()
        results = generator.generate_all_platforms(
            input_path='/fake/input.mp4',
            output_dir='/fake/output'
        )

        # Should have results for all platforms
        assert len(results) > 0
        # Each platform should have at least one format
        for platform_results in results.values():
            assert len(platform_results) > 0


class TestConvenienceFunctions:
    """Test convenience helper functions"""

    @patch('transcode.Transcoder')
    def test_transcode_to_mp4_helper(self, mock_transcoder_class):
        """Test transcode_to_mp4 convenience function"""
        mock_transcoder = MagicMock()
        mock_transcoder_class.return_value = mock_transcoder
        mock_transcoder.transcode.return_value = TranscodeResult(success=True)

        result = transcode_to_mp4(
            '/fake/input.avi',
            '/fake/output.mp4',
            width=1280,
            quality=90
        )

        assert result.success is True
        mock_transcoder.transcode.assert_called_once()
        call_args = mock_transcoder.transcode.call_args
        assert call_args[0][0] == '/fake/input.avi'
        assert call_args[0][1] == '/fake/output.mp4'
        assert call_args[0][2].output_format == OutputFormat.MP4

    @patch('transcode.Transcoder')
    def test_transcode_to_webp_helper(self, mock_transcoder_class):
        """Test transcode_to_webp convenience function"""
        mock_transcoder = MagicMock()
        mock_transcoder_class.return_value = mock_transcoder
        mock_transcoder.transcode.return_value = TranscodeResult(success=True)

        result = transcode_to_webp('/fake/input.gif', '/fake/output.webp')

        assert result.success is True
        call_args = mock_transcoder.transcode.call_args
        assert call_args[0][2].output_format == OutputFormat.WEBP

    @patch('transcode.Transcoder')
    def test_transcode_to_gif_helper(self, mock_transcoder_class):
        """Test transcode_to_gif convenience function"""
        mock_transcoder = MagicMock()
        mock_transcoder_class.return_value = mock_transcoder
        mock_transcoder.transcode.return_value = TranscodeResult(success=True)

        result = transcode_to_gif('/fake/input.mp4', '/fake/output.gif', fps=15)

        assert result.success is True
        call_args = mock_transcoder.transcode.call_args
        assert call_args[0][2].output_format == OutputFormat.GIF

    @patch('transcode.RenditionGenerator')
    def test_generate_platform_renditions_helper(self, mock_generator_class):
        """Test generate_platform_renditions convenience function"""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_renditions.return_value = {}

        result = generate_platform_renditions(
            '/fake/input.mp4',
            '/fake/output',
            platforms=[Platform.SLACK, Platform.DISCORD]
        )

        mock_generator.generate_renditions.assert_called_once_with(
            '/fake/input.mp4',
            '/fake/output',
            [Platform.SLACK, Platform.DISCORD]
        )

    @patch('transcode.RenditionGenerator')
    def test_generate_platform_renditions_all(self, mock_generator_class):
        """Test generate_platform_renditions with all platforms"""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_all_platforms.return_value = {}

        result = generate_platform_renditions(
            '/fake/input.mp4',
            '/fake/output',
            platforms=None
        )

        mock_generator.generate_all_platforms.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling"""

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_unsupported_output_format(self, mock_exists, mock_run):
        """Test error with unsupported output format"""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True

        transcoder = Transcoder()

        # This should fail since we're using an invalid format
        # But our Enum restricts this, so we test via mock
        options = TranscodeOptions(output_format=OutputFormat.MP4)
        options.output_format = "invalid"  # Force invalid

        with patch('transcode.MediaInfo.get_info') as mock_info:
            mock_info.return_value = {
                'width': 1920,
                'height': 1080,
                'duration': 10.0,
                'fps': 30
            }

            result = transcoder.transcode(
                '/fake/input.mp4',
                '/fake/output.xyz',
                options
            )

            assert result.success is False
            assert 'unsupported' in result.error.lower()

    def test_platform_spec_completeness(self):
        """Ensure all platform specs are complete"""
        for platform, spec in PLATFORM_SPECS.items():
            assert spec.name is not None
            assert spec.max_width > 0
            assert spec.max_height > 0
            assert spec.max_filesize_mb > 0
            assert len(spec.preferred_formats) > 0
            assert spec.notes != ""


class TestIntegration:
    """Integration tests (would require actual ffmpeg)"""

    def test_platform_enum_values(self):
        """Test platform enum has expected values"""
        platforms = [p.value for p in Platform]
        assert 'giphy' in platforms
        assert 'tenor' in platforms
        assert 'slack' in platforms
        assert 'discord' in platforms
        assert 'teams' in platforms

    def test_output_format_enum_values(self):
        """Test output format enum"""
        formats = [f.value for f in OutputFormat]
        assert 'mp4' in formats
        assert 'webp' in formats
        assert 'gif' in formats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
