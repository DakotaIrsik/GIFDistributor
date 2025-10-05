"""
Frame Sampler Module - Issue #11
Extract N evenly spaced frames from GIF/MP4 files

Features:
- Extract frames from GIF and MP4 files
- Support for evenly-spaced frame sampling
- Multiple output formats (PIL Image, bytes, file)
- Optimized for performance with large media files
- Error handling and validation
"""

import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union, BinaryIO
from dataclasses import dataclass
from enum import Enum
from PIL import Image


class MediaType(str, Enum):
    """Supported media types"""

    GIF = "gif"
    MP4 = "mp4"
    UNKNOWN = "unknown"


class OutputFormat(str, Enum):
    """Frame output format options"""

    PIL_IMAGE = "pil"  # PIL Image objects
    BYTES = "bytes"  # Raw image bytes (PNG format)
    FILE = "file"  # Save to files


@dataclass
class FrameInfo:
    """Information about an extracted frame"""

    index: int  # Frame index in original media
    timestamp_ms: Optional[float] = None  # Timestamp in milliseconds (for video)
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None


@dataclass
class SamplerResult:
    """Result from frame sampling operation"""

    frames: List[Union[Image.Image, bytes, str]]  # Frames in requested format
    frame_info: List[FrameInfo]  # Metadata for each frame
    total_frames: int  # Total frames in source media
    media_type: MediaType
    duration_ms: Optional[float] = None  # Total duration (for video)


class FrameSampler:
    """
    Extract evenly-spaced frames from GIF and MP4 files
    """

    @staticmethod
    def detect_media_type(file_path: str) -> MediaType:
        """
        Detect media type from file extension and/or content

        Args:
            file_path: Path to media file

        Returns:
            MediaType enum value
        """
        ext = Path(file_path).suffix.lower()

        if ext == ".gif":
            return MediaType.GIF
        elif ext in [".mp4", ".m4v", ".mov"]:
            return MediaType.MP4

        # Try to detect from content
        try:
            with open(file_path, "rb") as f:
                header = f.read(12)
                # Check for GIF magic number
                if header.startswith(b"GIF89a") or header.startswith(b"GIF87a"):
                    return MediaType.GIF
                # Check for MP4/MOV signatures
                if b"ftyp" in header:
                    return MediaType.MP4
        except Exception:
            pass

        return MediaType.UNKNOWN

    @staticmethod
    def get_gif_frame_count(file_path: str) -> int:
        """
        Get total number of frames in GIF

        Args:
            file_path: Path to GIF file

        Returns:
            Number of frames
        """
        with Image.open(file_path) as img:
            if not getattr(img, "is_animated", False):
                return 1

            frame_count = 0
            try:
                while True:
                    frame_count += 1
                    img.seek(img.tell() + 1)
            except EOFError:
                pass

        return frame_count

    @staticmethod
    def get_video_info(file_path: str) -> Tuple[int, float]:
        """
        Get video frame count and duration using ffprobe

        Args:
            file_path: Path to video file

        Returns:
            Tuple of (frame_count, duration_ms)
        """
        try:
            # Get frame count
            cmd_frames = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-count_packets",
                "-show_entries",
                "stream=nb_read_packets",
                "-of",
                "csv=p=0",
                file_path,
            ]
            result = subprocess.run(
                cmd_frames, capture_output=True, text=True, check=True
            )
            frame_count = int(result.stdout.strip())

            # Get duration
            cmd_duration = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                file_path,
            ]
            result = subprocess.run(
                cmd_duration, capture_output=True, text=True, check=True
            )
            duration_sec = float(result.stdout.strip())

            return frame_count, duration_sec * 1000

        except (subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Failed to get video info: {e}")

    @staticmethod
    def calculate_frame_indices(total_frames: int, num_samples: int) -> List[int]:
        """
        Calculate evenly-spaced frame indices

        Args:
            total_frames: Total number of frames
            num_samples: Number of frames to sample

        Returns:
            List of frame indices (0-based)
        """
        if num_samples <= 0:
            return []

        if num_samples >= total_frames:
            return list(range(total_frames))

        # Calculate step size for even spacing
        step = (total_frames - 1) / (num_samples - 1) if num_samples > 1 else 0

        indices = []
        for i in range(num_samples):
            index = round(i * step)
            indices.append(min(index, total_frames - 1))

        return indices

    @staticmethod
    def sample_gif(
        file_path: str,
        num_frames: int,
        output_format: OutputFormat = OutputFormat.PIL_IMAGE,
        output_dir: Optional[str] = None,
    ) -> SamplerResult:
        """
        Sample frames from GIF file

        Args:
            file_path: Path to GIF file
            num_frames: Number of frames to extract
            output_format: Format for output frames
            output_dir: Directory to save frames (required if output_format=FILE)

        Returns:
            SamplerResult with extracted frames
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        total_frames = FrameSampler.get_gif_frame_count(file_path)
        indices = FrameSampler.calculate_frame_indices(total_frames, num_frames)

        frames = []
        frame_info = []

        with Image.open(file_path) as img:
            for idx in indices:
                img.seek(idx)
                frame = img.copy().convert("RGB")

                info = FrameInfo(
                    index=idx, width=frame.width, height=frame.height, format="RGB"
                )
                frame_info.append(info)

                if output_format == OutputFormat.PIL_IMAGE:
                    frames.append(frame)
                elif output_format == OutputFormat.BYTES:
                    buffer = io.BytesIO()
                    frame.save(buffer, format="PNG")
                    frames.append(buffer.getvalue())
                elif output_format == OutputFormat.FILE:
                    if not output_dir:
                        raise ValueError("output_dir required for FILE output format")
                    os.makedirs(output_dir, exist_ok=True)
                    filename = f"frame_{idx:04d}.png"
                    filepath = os.path.join(output_dir, filename)
                    frame.save(filepath, format="PNG")
                    frames.append(filepath)

        return SamplerResult(
            frames=frames,
            frame_info=frame_info,
            total_frames=total_frames,
            media_type=MediaType.GIF,
        )

    @staticmethod
    def sample_video(
        file_path: str,
        num_frames: int,
        output_format: OutputFormat = OutputFormat.PIL_IMAGE,
        output_dir: Optional[str] = None,
    ) -> SamplerResult:
        """
        Sample frames from MP4/video file using ffmpeg

        Args:
            file_path: Path to video file
            num_frames: Number of frames to extract
            output_format: Format for output frames
            output_dir: Directory to save frames (required if output_format=FILE)

        Returns:
            SamplerResult with extracted frames
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        total_frames, duration_ms = FrameSampler.get_video_info(file_path)
        indices = FrameSampler.calculate_frame_indices(total_frames, num_frames)

        frames = []
        frame_info = []

        # Create temp directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            for idx in indices:
                # Calculate timestamp
                timestamp_ms = (
                    (idx / total_frames) * duration_ms if total_frames > 0 else 0
                )
                timestamp_sec = timestamp_ms / 1000

                # Extract frame using ffmpeg
                temp_frame = os.path.join(temp_dir, f"frame_{idx}.png")
                cmd = [
                    "ffmpeg",
                    "-ss",
                    str(timestamp_sec),
                    "-i",
                    file_path,
                    "-frames:v",
                    "1",
                    "-y",
                    temp_frame,
                ]

                try:
                    subprocess.run(
                        cmd,
                        capture_output=True,
                        check=True,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                        ),
                    )
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"ffmpeg failed: {e.stderr.decode()}")

                # Load and process frame
                with Image.open(temp_frame) as frame:
                    frame = frame.convert("RGB")

                    info = FrameInfo(
                        index=idx,
                        timestamp_ms=timestamp_ms,
                        width=frame.width,
                        height=frame.height,
                        format="RGB",
                    )
                    frame_info.append(info)

                    if output_format == OutputFormat.PIL_IMAGE:
                        frames.append(frame.copy())
                    elif output_format == OutputFormat.BYTES:
                        buffer = io.BytesIO()
                        frame.save(buffer, format="PNG")
                        frames.append(buffer.getvalue())
                    elif output_format == OutputFormat.FILE:
                        if not output_dir:
                            raise ValueError(
                                "output_dir required for FILE output format"
                            )
                        os.makedirs(output_dir, exist_ok=True)
                        filename = f"frame_{idx:04d}.png"
                        filepath = os.path.join(output_dir, filename)
                        frame.save(filepath, format="PNG")
                        frames.append(filepath)

        return SamplerResult(
            frames=frames,
            frame_info=frame_info,
            total_frames=total_frames,
            media_type=MediaType.MP4,
            duration_ms=duration_ms,
        )

    @staticmethod
    def sample_media(
        file_path: str,
        num_frames: int,
        output_format: OutputFormat = OutputFormat.PIL_IMAGE,
        output_dir: Optional[str] = None,
        media_type: Optional[MediaType] = None,
    ) -> SamplerResult:
        """
        Sample frames from GIF or MP4 (auto-detects type)

        Args:
            file_path: Path to media file
            num_frames: Number of frames to extract
            output_format: Format for output frames
            output_dir: Directory to save frames (required if output_format=FILE)
            media_type: Force specific media type (auto-detect if None)

        Returns:
            SamplerResult with extracted frames
        """
        if media_type is None:
            media_type = FrameSampler.detect_media_type(file_path)

        if media_type == MediaType.GIF:
            return FrameSampler.sample_gif(
                file_path, num_frames, output_format, output_dir
            )
        elif media_type == MediaType.MP4:
            return FrameSampler.sample_video(
                file_path, num_frames, output_format, output_dir
            )
        else:
            raise ValueError(f"Unsupported media type: {media_type}")


# Convenience functions


def sample_frames(
    file_path: str, num_frames: int, output_format: str = "pil"
) -> List[Union[Image.Image, bytes]]:
    """
    Quick helper to sample frames from media file

    Args:
        file_path: Path to media file (GIF or MP4)
        num_frames: Number of frames to extract
        output_format: "pil" for PIL Images or "bytes" for PNG bytes

    Returns:
        List of frames in requested format
    """
    fmt = OutputFormat.PIL_IMAGE if output_format == "pil" else OutputFormat.BYTES
    result = FrameSampler.sample_media(file_path, num_frames, output_format=fmt)
    return result.frames


def get_frame_count(file_path: str) -> int:
    """
    Quick helper to get frame count from media file

    Args:
        file_path: Path to media file

    Returns:
        Total number of frames
    """
    media_type = FrameSampler.detect_media_type(file_path)

    if media_type == MediaType.GIF:
        return FrameSampler.get_gif_frame_count(file_path)
    elif media_type == MediaType.MP4:
        count, _ = FrameSampler.get_video_info(file_path)
        return count
    else:
        raise ValueError(f"Unsupported media type: {media_type}")


if __name__ == "__main__":
    import sys

    print("Frame Sampler - Extract evenly-spaced frames from GIF/MP4")
    print("=" * 60)

    if len(sys.argv) < 3:
        print("Usage: python frame_sampler.py <file_path> <num_frames> [output_dir]")
        sys.exit(1)

    file_path = sys.argv[1]
    num_frames = int(sys.argv[2])
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "sampled_frames"

    # Sample frames and save to files
    result = FrameSampler.sample_media(
        file_path, num_frames, output_format=OutputFormat.FILE, output_dir=output_dir
    )

    print(f"\nMedia Type: {result.media_type.value}")
    print(f"Total Frames: {result.total_frames}")
    if result.duration_ms:
        print(f"Duration: {result.duration_ms/1000:.2f} seconds")

    print(f"\nExtracted {len(result.frames)} frames:")
    for i, (frame_path, info) in enumerate(zip(result.frames, result.frame_info)):
        print(f"  {i+1}. {frame_path} (frame {info.index}, {info.width}x{info.height})")

    print(f"\nFrames saved to: {output_dir}")
