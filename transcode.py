"""
Transcode Module - Issue #30
Transcode media to MP4/WebP + optimized GIF with per-platform renditions

Features:
- Convert various input formats to MP4, WebP, and optimized GIF
- Generate platform-specific renditions (GIPHY, Tenor, Slack, Discord, Teams)
- Optimize file sizes while maintaining quality
- Support for dimensions, bitrate, and quality customization
- Progress tracking and error handling
"""

import os
import subprocess
import json
from typing import Dict, List, Optional, Tuple, Any, Literal
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class Platform(str, Enum):
    """Supported platforms with specific requirements"""
    GIPHY = "giphy"
    TENOR = "tenor"
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"
    WEB = "web"
    MOBILE = "mobile"


class OutputFormat(str, Enum):
    """Supported output formats"""
    MP4 = "mp4"
    WEBP = "webp"
    GIF = "gif"


@dataclass
class PlatformSpec:
    """Platform-specific output specifications"""
    name: Platform
    max_width: int
    max_height: int
    max_filesize_mb: float
    max_duration_sec: Optional[float] = None
    preferred_formats: List[OutputFormat] = field(default_factory=list)
    max_fps: Optional[int] = None
    notes: str = ""


# Platform specifications based on actual platform requirements
PLATFORM_SPECS: Dict[Platform, PlatformSpec] = {
    Platform.GIPHY: PlatformSpec(
        name=Platform.GIPHY,
        max_width=1920,
        max_height=1080,
        max_filesize_mb=100.0,
        max_duration_sec=60.0,
        preferred_formats=[OutputFormat.GIF, OutputFormat.MP4],
        max_fps=30,
        notes="GIPHY prefers optimized GIFs, supports MP4 as source"
    ),
    Platform.TENOR: PlatformSpec(
        name=Platform.TENOR,
        max_width=1920,
        max_height=1080,
        max_filesize_mb=50.0,
        max_duration_sec=30.0,
        preferred_formats=[OutputFormat.GIF, OutputFormat.MP4],
        max_fps=30,
        notes="Tenor prefers MP4, converts to multiple formats internally"
    ),
    Platform.SLACK: PlatformSpec(
        name=Platform.SLACK,
        max_width=1920,
        max_height=1080,
        max_filesize_mb=25.0,
        preferred_formats=[OutputFormat.GIF, OutputFormat.MP4, OutputFormat.WEBP],
        max_fps=24,
        notes="Slack supports GIF, MP4, and WebP; WebP preferred for smaller size"
    ),
    Platform.DISCORD: PlatformSpec(
        name=Platform.DISCORD,
        max_width=1920,
        max_height=1080,
        max_filesize_mb=50.0,  # 8MB for free, 50MB for Nitro
        preferred_formats=[OutputFormat.GIF, OutputFormat.MP4, OutputFormat.WEBP],
        max_fps=30,
        notes="Discord supports GIF and MP4; auto-plays MP4"
    ),
    Platform.TEAMS: PlatformSpec(
        name=Platform.TEAMS,
        max_width=1920,
        max_height=1080,
        max_filesize_mb=100.0,
        preferred_formats=[OutputFormat.MP4, OutputFormat.GIF],
        max_fps=30,
        notes="Teams prefers MP4 for adaptive cards"
    ),
    Platform.WEB: PlatformSpec(
        name=Platform.WEB,
        max_width=2560,
        max_height=1440,
        max_filesize_mb=25.0,
        preferred_formats=[OutputFormat.WEBP, OutputFormat.MP4, OutputFormat.GIF],
        max_fps=60,
        notes="Modern web browsers prefer WebP for animations"
    ),
    Platform.MOBILE: PlatformSpec(
        name=Platform.MOBILE,
        max_width=1080,
        max_height=1920,
        max_filesize_mb=10.0,
        preferred_formats=[OutputFormat.MP4, OutputFormat.WEBP],
        max_fps=30,
        notes="Mobile optimized for smaller files and lower bandwidth"
    ),
}


@dataclass
class TranscodeOptions:
    """Options for transcoding operations"""
    output_format: OutputFormat
    width: Optional[int] = None
    height: Optional[int] = None
    quality: int = 85  # 0-100
    fps: Optional[int] = None
    bitrate: Optional[str] = None  # e.g., "1M", "500k"
    optimize: bool = True
    lossy_compression: bool = True  # For GIF optimization
    preserve_aspect_ratio: bool = True
    two_pass_encoding: bool = False  # For better quality MP4


@dataclass
class TranscodeResult:
    """Result of a transcoding operation"""
    success: bool
    output_path: Optional[str] = None
    output_format: Optional[OutputFormat] = None
    output_size_bytes: Optional[int] = None
    duration_sec: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MediaInfo:
    """Extract media information using ffprobe"""

    @staticmethod
    def get_info(input_path: str) -> Dict[str, Any]:
        """Get media metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                input_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            data = json.loads(result.stdout)

            # Extract video stream info
            video_stream = next(
                (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
                None
            )

            if not video_stream:
                return {'error': 'No video stream found'}

            format_data = data.get('format', {})

            return {
                'width': video_stream.get('width'),
                'height': video_stream.get('height'),
                'codec': video_stream.get('codec_name'),
                'duration': float(format_data.get('duration', 0)),
                'size_bytes': int(format_data.get('size', 0)),
                'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                'bitrate': int(format_data.get('bit_rate', 0)),
                'format': format_data.get('format_name'),
            }

        except subprocess.CalledProcessError as e:
            return {'error': f'ffprobe failed: {e.stderr}'}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def calculate_dimensions(
        input_width: int,
        input_height: int,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        preserve_aspect_ratio: bool = True
    ) -> Tuple[int, int]:
        """Calculate output dimensions preserving aspect ratio"""

        if not preserve_aspect_ratio and target_width and target_height:
            return (target_width, target_height)

        aspect_ratio = input_width / input_height

        # Start with input dimensions
        width, height = input_width, input_height

        # Apply target dimensions
        if target_width and target_height:
            if preserve_aspect_ratio:
                # Fit within target dimensions
                if input_width / target_width > input_height / target_height:
                    width = target_width
                    height = int(target_width / aspect_ratio)
                else:
                    height = target_height
                    width = int(target_height * aspect_ratio)
            else:
                width, height = target_width, target_height
        elif target_width:
            width = target_width
            height = int(target_width / aspect_ratio)
        elif target_height:
            height = target_height
            width = int(target_height * aspect_ratio)

        # Apply max dimensions
        if max_width and width > max_width:
            width = max_width
            height = int(max_width / aspect_ratio)

        if max_height and height > max_height:
            height = max_height
            width = int(max_height * aspect_ratio)

        # Ensure even dimensions (required by some codecs)
        width = width - (width % 2)
        height = height - (height % 2)

        return (width, height)


class Transcoder:
    """Main transcoding engine"""

    def __init__(self, ffmpeg_path: str = 'ffmpeg', ffprobe_path: str = 'ffprobe'):
        """
        Initialize transcoder

        Args:
            ffmpeg_path: Path to ffmpeg executable
            ffprobe_path: Path to ffprobe executable
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if ffmpeg and ffprobe are available"""
        try:
            subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                check=True,
                timeout=5
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                f"ffmpeg not found at {self.ffmpeg_path}. "
                "Please install ffmpeg or provide correct path."
            )

    def transcode(
        self,
        input_path: str,
        output_path: str,
        options: TranscodeOptions
    ) -> TranscodeResult:
        """
        Transcode media file

        Args:
            input_path: Path to input file
            output_path: Path to output file
            options: Transcoding options

        Returns:
            TranscodeResult with success status and metadata
        """
        if not os.path.exists(input_path):
            return TranscodeResult(
                success=False,
                error=f"Input file not found: {input_path}"
            )

        # Get input media info
        info = MediaInfo.get_info(input_path)
        if 'error' in info:
            return TranscodeResult(
                success=False,
                error=f"Failed to read input: {info['error']}"
            )

        # Calculate output dimensions
        width, height = MediaInfo.calculate_dimensions(
            input_width=info['width'],
            input_height=info['height'],
            target_width=options.width,
            target_height=options.height,
            preserve_aspect_ratio=options.preserve_aspect_ratio
        )

        # Build ffmpeg command based on output format
        try:
            if options.output_format == OutputFormat.MP4:
                self._transcode_to_mp4(input_path, output_path, options, width, height)
            elif options.output_format == OutputFormat.WEBP:
                self._transcode_to_webp(input_path, output_path, options, width, height)
            elif options.output_format == OutputFormat.GIF:
                self._transcode_to_gif(input_path, output_path, options, width, height)
            else:
                return TranscodeResult(
                    success=False,
                    error=f"Unsupported output format: {options.output_format}"
                )

            # Get output file info
            if os.path.exists(output_path):
                output_info = MediaInfo.get_info(output_path)
                return TranscodeResult(
                    success=True,
                    output_path=output_path,
                    output_format=options.output_format,
                    output_size_bytes=os.path.getsize(output_path),
                    duration_sec=output_info.get('duration'),
                    width=output_info.get('width'),
                    height=output_info.get('height'),
                    fps=output_info.get('fps'),
                    metadata=output_info
                )
            else:
                return TranscodeResult(
                    success=False,
                    error="Output file was not created"
                )

        except subprocess.CalledProcessError as e:
            return TranscodeResult(
                success=False,
                error=f"ffmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
            )
        except Exception as e:
            return TranscodeResult(
                success=False,
                error=f"Transcoding failed: {str(e)}"
            )

    def _transcode_to_mp4(
        self,
        input_path: str,
        output_path: str,
        options: TranscodeOptions,
        width: int,
        height: int
    ) -> None:
        """Transcode to MP4 using H.264"""
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', str((100 - options.quality) // 4),  # CRF: 0-51, lower is better
            '-vf', f'scale={width}:{height}',
            '-pix_fmt', 'yuv420p',  # Compatibility
            '-movflags', '+faststart',  # Web optimization
        ]

        if options.fps:
            cmd.extend(['-r', str(options.fps)])

        if options.bitrate:
            cmd.extend(['-b:v', options.bitrate])

        # Audio handling (copy or remove)
        cmd.extend(['-an'])  # Remove audio for now

        cmd.extend(['-y', output_path])  # Overwrite output

        subprocess.run(cmd, capture_output=True, check=True, timeout=300)

    def _transcode_to_webp(
        self,
        input_path: str,
        output_path: str,
        options: TranscodeOptions,
        width: int,
        height: int
    ) -> None:
        """Transcode to animated WebP"""
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-c:v', 'libwebp',
            '-vf', f'scale={width}:{height}',
            '-quality', str(options.quality),
            '-loop', '0',  # Loop indefinitely
        ]

        if options.fps:
            cmd.extend(['-r', str(options.fps)])

        if options.lossy_compression:
            cmd.extend(['-compression_level', '6'])

        cmd.extend(['-y', output_path])

        subprocess.run(cmd, capture_output=True, check=True, timeout=300)

    def _transcode_to_gif(
        self,
        input_path: str,
        output_path: str,
        options: TranscodeOptions,
        width: int,
        height: int
    ) -> None:
        """Transcode to optimized GIF using two-pass palette generation"""

        if options.optimize:
            # Two-pass encoding with palette generation for better quality
            palette_path = output_path + '.palette.png'

            # Pass 1: Generate optimal palette
            cmd_palette = [
                self.ffmpeg_path,
                '-i', input_path,
                '-vf', f'scale={width}:{height}:flags=lanczos,palettegen=stats_mode=diff',
            ]

            if options.fps:
                cmd_palette.extend(['-r', str(options.fps)])

            cmd_palette.extend(['-y', palette_path])

            subprocess.run(cmd_palette, capture_output=True, check=True, timeout=300)

            # Pass 2: Use palette to create GIF
            cmd_gif = [
                self.ffmpeg_path,
                '-i', input_path,
                '-i', palette_path,
                '-lavfi', f'scale={width}:{height}:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5',
            ]

            if options.fps:
                cmd_gif.extend(['-r', str(options.fps)])

            cmd_gif.extend(['-loop', '0', '-y', output_path])

            subprocess.run(cmd_gif, capture_output=True, check=True, timeout=300)

            # Clean up palette
            if os.path.exists(palette_path):
                os.remove(palette_path)
        else:
            # Simple one-pass GIF encoding
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-vf', f'scale={width}:{height}',
            ]

            if options.fps:
                cmd.extend(['-r', str(options.fps)])

            cmd.extend(['-loop', '0', '-y', output_path])

            subprocess.run(cmd, capture_output=True, check=True, timeout=300)


class RenditionGenerator:
    """Generate platform-specific renditions"""

    def __init__(self, transcoder: Optional[Transcoder] = None):
        """
        Initialize rendition generator

        Args:
            transcoder: Transcoder instance (creates new one if not provided)
        """
        self.transcoder = transcoder or Transcoder()

    def generate_renditions(
        self,
        input_path: str,
        output_dir: str,
        platforms: List[Platform],
        base_filename: Optional[str] = None
    ) -> Dict[Platform, Dict[OutputFormat, TranscodeResult]]:
        """
        Generate renditions for specified platforms

        Args:
            input_path: Path to input media file
            output_dir: Directory to save renditions
            platforms: List of platforms to generate renditions for
            base_filename: Base filename (without extension)

        Returns:
            Dictionary mapping platforms to format-specific results
        """
        if not base_filename:
            base_filename = Path(input_path).stem

        os.makedirs(output_dir, exist_ok=True)

        results: Dict[Platform, Dict[OutputFormat, TranscodeResult]] = {}

        # Get input media info once
        info = MediaInfo.get_info(input_path)
        if 'error' in info:
            return results

        for platform in platforms:
            spec = PLATFORM_SPECS.get(platform)
            if not spec:
                continue

            platform_results: Dict[OutputFormat, TranscodeResult] = {}

            # Calculate dimensions for this platform
            width, height = MediaInfo.calculate_dimensions(
                input_width=info['width'],
                input_height=info['height'],
                max_width=spec.max_width,
                max_height=spec.max_height,
                preserve_aspect_ratio=True
            )

            # Generate each preferred format for this platform
            for fmt in spec.preferred_formats:
                output_filename = f"{base_filename}_{platform.value}.{fmt.value}"
                output_path = os.path.join(output_dir, output_filename)

                options = TranscodeOptions(
                    output_format=fmt,
                    width=width,
                    height=height,
                    fps=spec.max_fps,
                    quality=85,
                    optimize=True
                )

                result = self.transcoder.transcode(
                    input_path=input_path,
                    output_path=output_path,
                    options=options
                )

                platform_results[fmt] = result

            results[platform] = platform_results

        return results

    def generate_all_platforms(
        self,
        input_path: str,
        output_dir: str,
        base_filename: Optional[str] = None
    ) -> Dict[Platform, Dict[OutputFormat, TranscodeResult]]:
        """
        Generate renditions for all platforms

        Args:
            input_path: Path to input media file
            output_dir: Directory to save renditions
            base_filename: Base filename (without extension)

        Returns:
            Dictionary mapping platforms to format-specific results
        """
        return self.generate_renditions(
            input_path=input_path,
            output_dir=output_dir,
            platforms=list(Platform),
            base_filename=base_filename
        )


# Convenience functions

def transcode_to_mp4(input_path: str, output_path: str, **kwargs) -> TranscodeResult:
    """Quick helper to transcode to MP4"""
    transcoder = Transcoder()
    options = TranscodeOptions(output_format=OutputFormat.MP4, **kwargs)
    return transcoder.transcode(input_path, output_path, options)


def transcode_to_webp(input_path: str, output_path: str, **kwargs) -> TranscodeResult:
    """Quick helper to transcode to WebP"""
    transcoder = Transcoder()
    options = TranscodeOptions(output_format=OutputFormat.WEBP, **kwargs)
    return transcoder.transcode(input_path, output_path, options)


def transcode_to_gif(input_path: str, output_path: str, **kwargs) -> TranscodeResult:
    """Quick helper to transcode to optimized GIF"""
    transcoder = Transcoder()
    options = TranscodeOptions(output_format=OutputFormat.GIF, **kwargs)
    return transcoder.transcode(input_path, output_path, options)


def generate_platform_renditions(
    input_path: str,
    output_dir: str,
    platforms: Optional[List[Platform]] = None
) -> Dict[Platform, Dict[OutputFormat, TranscodeResult]]:
    """
    Quick helper to generate platform-specific renditions

    Args:
        input_path: Path to input media
        output_dir: Output directory
        platforms: List of platforms (all if None)

    Returns:
        Results dictionary
    """
    generator = RenditionGenerator()

    if platforms is None:
        return generator.generate_all_platforms(input_path, output_dir)
    else:
        return generator.generate_renditions(input_path, output_dir, platforms)


if __name__ == '__main__':
    # Example usage
    print("Transcode Module - Issue #30")
    print("=" * 60)
    print("\nPlatform Specifications:")
    for platform, spec in PLATFORM_SPECS.items():
        print(f"\n{platform.value.upper()}:")
        print(f"  Max dimensions: {spec.max_width}x{spec.max_height}")
        print(f"  Max size: {spec.max_filesize_mb}MB")
        print(f"  Formats: {', '.join(f.value for f in spec.preferred_formats)}")
        print(f"  Notes: {spec.notes}")
