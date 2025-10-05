"""
Transcode Module for GIF Distributor
Handles transcoding GIF to MP4/WebP with GIF fallback
Issue: #29
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, List
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats"""

    MP4 = "mp4"
    WEBP = "webp"
    GIF = "gif"


class TranscodeError(Exception):
    """Exception raised for transcoding errors"""

    pass


class Transcoder:
    """Handles transcoding of GIF assets to various formats"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """
        Initialize the transcoder

        Args:
            ffmpeg_path: Path to ffmpeg executable (default: "ffmpeg")
            ffprobe_path: Path to ffprobe executable (default: "ffprobe")
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> None:
        """Verify that ffmpeg and ffprobe are available"""
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
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise TranscodeError(f"ffmpeg/ffprobe not found or not working: {e}")

    def get_media_info(self, input_path: str) -> Dict:
        """
        Get media file information using ffprobe

        Args:
            input_path: Path to the input file

        Returns:
            Dictionary containing media information

        Raises:
            TranscodeError: If ffprobe fails
        """
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    input_path,
                ],
                capture_output=True,
                check=True,
                timeout=10,
            )
            import json

            info = json.loads(result.stdout)

            # Extract relevant info
            video_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )

            return {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size": int(info.get("format", {}).get("size", 0)),
                "width": int(video_stream.get("width", 0)) if video_stream else 0,
                "height": int(video_stream.get("height", 0)) if video_stream else 0,
                "codec": (
                    video_stream.get("codec_name", "unknown")
                    if video_stream
                    else "unknown"
                ),
            }
        except subprocess.SubprocessError as e:
            raise TranscodeError(f"Failed to get media info: {e}")
        except json.JSONDecodeError as e:
            raise TranscodeError(f"Failed to parse ffprobe output: {e}")

    def transcode_to_mp4(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        quality: str = "high",
        max_width: Optional[int] = None,
    ) -> str:
        """
        Transcode GIF to MP4 format

        Args:
            input_path: Path to input GIF file
            output_path: Path to output MP4 file (auto-generated if None)
            quality: Quality preset ("low", "medium", "high")
            max_width: Maximum width for output (preserves aspect ratio)

        Returns:
            Path to the output MP4 file

        Raises:
            TranscodeError: If transcoding fails
        """
        if output_path is None:
            output_path = str(Path(input_path).with_suffix(".mp4"))

        # Quality settings
        quality_settings = {
            "low": {"crf": "28", "preset": "fast"},
            "medium": {"crf": "23", "preset": "medium"},
            "high": {"crf": "18", "preset": "slow"},
        }
        settings = quality_settings.get(quality, quality_settings["high"])

        # Build ffmpeg command
        cmd = [
            self.ffmpeg_path,
            "-i",
            input_path,
            "-movflags",
            "faststart",  # Enable streaming
            "-pix_fmt",
            "yuv420p",  # Ensure compatibility
            "-vcodec",
            "libx264",
            "-crf",
            settings["crf"],
            "-preset",
            settings["preset"],
        ]

        # Add scaling if max_width specified
        if max_width:
            cmd.extend(["-vf", f"scale='min({max_width},iw)':-2"])

        cmd.extend(["-y", output_path])  # Overwrite output file

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            return output_path
        except subprocess.SubprocessError as e:
            raise TranscodeError(f"Failed to transcode to MP4: {e}")

    def transcode_to_webp(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        quality: int = 80,
        lossless: bool = False,
    ) -> str:
        """
        Transcode GIF to WebP format

        Args:
            input_path: Path to input GIF file
            output_path: Path to output WebP file (auto-generated if None)
            quality: Quality level 0-100 (default: 80)
            lossless: Use lossless compression (default: False)

        Returns:
            Path to the output WebP file

        Raises:
            TranscodeError: If transcoding fails
        """
        if output_path is None:
            output_path = str(Path(input_path).with_suffix(".webp"))

        cmd = [
            self.ffmpeg_path,
            "-i",
            input_path,
        ]

        if lossless:
            cmd.extend(["-lossless", "1"])
        else:
            cmd.extend(["-quality", str(quality)])

        cmd.extend(["-y", output_path])

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            return output_path
        except subprocess.SubprocessError as e:
            raise TranscodeError(f"Failed to transcode to WebP: {e}")

    def optimize_gif(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        max_colors: int = 256,
        max_width: Optional[int] = None,
    ) -> str:
        """
        Optimize GIF file (reduce size while maintaining quality)

        Args:
            input_path: Path to input GIF file
            output_path: Path to output GIF file (auto-generated if None)
            max_colors: Maximum colors in palette (default: 256)
            max_width: Maximum width for output (preserves aspect ratio)

        Returns:
            Path to the optimized GIF file

        Raises:
            TranscodeError: If optimization fails
        """
        if output_path is None:
            base = Path(input_path)
            output_path = str(base.parent / f"{base.stem}_optimized{base.suffix}")

        # Build filter chain
        filters = []
        if max_width:
            filters.append(f"scale='min({max_width},iw)':-1:flags=lanczos")

        # Add palette generation for better color optimization
        filters.append(
            f"split[s0][s1];[s0]palettegen=max_colors={max_colors}[p];[s1][p]paletteuse"
        )

        filter_str = ",".join(filters) if filters else None

        cmd = [
            self.ffmpeg_path,
            "-i",
            input_path,
        ]

        if filter_str:
            cmd.extend(["-vf", filter_str])

        cmd.extend(["-y", output_path])

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            return output_path
        except subprocess.SubprocessError as e:
            raise TranscodeError(f"Failed to optimize GIF: {e}")

    def transcode_all_formats(
        self, input_path: str, output_dir: Optional[str] = None, quality: str = "high"
    ) -> Dict[str, str]:
        """
        Transcode to all supported formats (MP4, WebP, optimized GIF)

        Args:
            input_path: Path to input GIF file
            output_dir: Directory for output files (uses input directory if None)
            quality: Quality preset for MP4 ("low", "medium", "high")

        Returns:
            Dictionary mapping format names to output file paths

        Raises:
            TranscodeError: If any transcoding operation fails
        """
        if output_dir is None:
            output_dir = str(Path(input_path).parent)

        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        base_name = Path(input_path).stem

        results = {}

        # MP4
        mp4_path = str(output_dir_path / f"{base_name}.mp4")
        results["mp4"] = self.transcode_to_mp4(input_path, mp4_path, quality=quality)

        # WebP
        webp_path = str(output_dir_path / f"{base_name}.webp")
        results["webp"] = self.transcode_to_webp(input_path, webp_path)

        # Optimized GIF
        gif_path = str(output_dir_path / f"{base_name}_optimized.gif")
        results["gif"] = self.optimize_gif(input_path, gif_path)

        return results


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes

    Args:
        file_path: Path to file

    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def get_size_reduction(original_path: str, transcoded_path: str) -> float:
    """
    Calculate size reduction percentage

    Args:
        original_path: Path to original file
        transcoded_path: Path to transcoded file

    Returns:
        Percentage reduction (positive means smaller, negative means larger)
    """
    original_size = get_file_size(original_path)
    transcoded_size = get_file_size(transcoded_path)

    if original_size == 0:
        return 0.0

    reduction = ((original_size - transcoded_size) / original_size) * 100
    return reduction
