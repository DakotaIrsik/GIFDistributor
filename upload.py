"""
Resumable upload module with chunking, deduplication, and progress tracking.

This module provides functionality for:
- Chunked uploads with resumable capability
- Content-based deduplication using SHA-256 hashing
- Upload session management
- Progress tracking and validation
- Metadata handling
"""

import hashlib
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, BinaryIO
from pathlib import Path


class UploadStatus(Enum):
    """Upload session status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class UploadChunk:
    """Represents a single upload chunk."""
    chunk_index: int
    chunk_size: int
    chunk_hash: str
    offset: int
    uploaded: bool = False
    uploaded_at: Optional[float] = None


@dataclass
class UploadSession:
    """Represents an upload session for resumable uploads."""
    session_id: str
    file_name: str
    file_size: int
    content_type: str
    chunk_size: int
    total_chunks: int
    chunks: List[UploadChunk] = field(default_factory=list)
    status: UploadStatus = UploadStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    file_hash: Optional[str] = None
    asset_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def get_progress(self) -> float:
        """Get upload progress as percentage (0-100)."""
        if self.total_chunks == 0:
            return 0.0
        uploaded_chunks = sum(1 for chunk in self.chunks if chunk.uploaded)
        return (uploaded_chunks / self.total_chunks) * 100

    def get_uploaded_bytes(self) -> int:
        """Get total uploaded bytes."""
        return sum(chunk.chunk_size for chunk in self.chunks if chunk.uploaded)

    def get_missing_chunks(self) -> List[int]:
        """Get indices of chunks that haven't been uploaded."""
        return [chunk.chunk_index for chunk in self.chunks if not chunk.uploaded]

    def is_complete(self) -> bool:
        """Check if all chunks have been uploaded."""
        return all(chunk.uploaded for chunk in self.chunks)


class UploadManager:
    """
    Manages resumable uploads with chunking and deduplication.

    Features:
    - Chunked uploads with configurable chunk size
    - Session-based resumable uploads
    - Content deduplication via SHA-256 hashing
    - Progress tracking
    - Validation and integrity checks
    """

    DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB
    MAX_CHUNK_SIZE = 100 * 1024 * 1024    # 100 MB
    MIN_CHUNK_SIZE = 256 * 1024            # 256 KB

    def __init__(self, storage_path: str = "./uploads", chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize upload manager.

        Args:
            storage_path: Directory to store uploaded files
            chunk_size: Size of each upload chunk in bytes
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        if chunk_size < self.MIN_CHUNK_SIZE or chunk_size > self.MAX_CHUNK_SIZE:
            raise ValueError(f"Chunk size must be between {self.MIN_CHUNK_SIZE} and {self.MAX_CHUNK_SIZE}")

        self.chunk_size = chunk_size
        self.sessions: Dict[str, UploadSession] = {}
        self.dedupe_index: Dict[str, str] = {}  # file_hash -> asset_id

    def create_session(
        self,
        file_name: str,
        file_size: int,
        content_type: str,
        metadata: Optional[Dict] = None
    ) -> UploadSession:
        """
        Create a new upload session.

        Args:
            file_name: Name of the file being uploaded
            file_size: Total size of the file in bytes
            content_type: MIME type of the file
            metadata: Optional metadata dictionary

        Returns:
            UploadSession object

        Raises:
            ValueError: If file_size is 0 or negative
        """
        if file_size <= 0:
            raise ValueError("File size must be greater than 0")

        session_id = self._generate_session_id(file_name, file_size)
        # Use smaller chunk size for small files
        effective_chunk_size = min(self.chunk_size, file_size)
        total_chunks = (file_size + effective_chunk_size - 1) // effective_chunk_size

        chunks = []
        for i in range(total_chunks):
            offset = i * effective_chunk_size
            chunk_size = min(effective_chunk_size, file_size - offset)
            chunks.append(UploadChunk(
                chunk_index=i,
                chunk_size=chunk_size,
                chunk_hash="",  # Will be set when chunk is uploaded
                offset=offset
            ))

        session = UploadSession(
            session_id=session_id,
            file_name=file_name,
            file_size=file_size,
            content_type=content_type,
            chunk_size=effective_chunk_size,
            total_chunks=total_chunks,
            chunks=chunks,
            metadata=metadata or {}
        )

        self.sessions[session_id] = session
        return session

    def upload_chunk(
        self,
        session_id: str,
        chunk_index: int,
        chunk_data: bytes
    ) -> Tuple[bool, Optional[str]]:
        """
        Upload a single chunk.

        Args:
            session_id: Upload session ID
            chunk_index: Index of the chunk being uploaded
            chunk_data: Binary data of the chunk

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if session_id not in self.sessions:
            return False, "Session not found"

        session = self.sessions[session_id]

        if session.status == UploadStatus.COMPLETED:
            return False, "Upload already completed"

        if session.status == UploadStatus.CANCELLED:
            return False, "Upload cancelled"

        if chunk_index >= session.total_chunks:
            return False, f"Invalid chunk index: {chunk_index}"

        chunk = session.chunks[chunk_index]

        # Validate chunk size
        expected_size = chunk.chunk_size
        if len(chunk_data) != expected_size:
            return False, f"Chunk size mismatch: expected {expected_size}, got {len(chunk_data)}"

        # Calculate chunk hash
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()

        # Store chunk
        chunk_path = self._get_chunk_path(session_id, chunk_index)
        chunk_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(chunk_path, 'wb') as f:
                f.write(chunk_data)
        except Exception as e:
            return False, f"Failed to write chunk: {str(e)}"

        # Update chunk metadata
        chunk.chunk_hash = chunk_hash
        chunk.uploaded = True
        chunk.uploaded_at = time.time()

        # Update session
        session.status = UploadStatus.IN_PROGRESS
        session.updated_at = time.time()

        return True, None

    def finalize_upload(self, session_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Finalize upload by assembling chunks and checking for duplicates.

        Args:
            session_id: Upload session ID

        Returns:
            Tuple of (success: bool, error_message: Optional[str], asset_id: Optional[str])
        """
        if session_id not in self.sessions:
            return False, "Session not found", None

        session = self.sessions[session_id]

        if not session.is_complete():
            missing = session.get_missing_chunks()
            return False, f"Upload incomplete. Missing chunks: {missing}", None

        # Assemble file from chunks
        final_path = self.storage_path / session_id / "final"
        final_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(final_path, 'wb') as outfile:
                for chunk in session.chunks:
                    chunk_path = self._get_chunk_path(session_id, chunk.chunk_index)
                    with open(chunk_path, 'rb') as infile:
                        outfile.write(infile.read())
        except Exception as e:
            return False, f"Failed to assemble file: {str(e)}", None

        # Calculate final file hash
        file_hash = self._calculate_file_hash(final_path)
        session.file_hash = file_hash

        # Check for duplicate
        if file_hash in self.dedupe_index:
            existing_asset_id = self.dedupe_index[file_hash]
            session.asset_id = existing_asset_id
            session.status = UploadStatus.COMPLETED
            session.completed_at = time.time()

            # Clean up chunks since we have a duplicate
            self._cleanup_chunks(session_id)

            return True, None, existing_asset_id

        # Generate new asset ID
        asset_id = self._generate_asset_id(file_hash)
        session.asset_id = asset_id
        session.status = UploadStatus.COMPLETED
        session.completed_at = time.time()

        # Update dedupe index
        self.dedupe_index[file_hash] = asset_id

        # Move file to permanent storage
        asset_path = self.storage_path / "assets" / asset_id
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.rename(asset_path)

        # Clean up chunks
        self._cleanup_chunks(session_id)

        return True, None, asset_id

    def get_session(self, session_id: str) -> Optional[UploadSession]:
        """Get upload session by ID."""
        return self.sessions.get(session_id)

    def cancel_session(self, session_id: str) -> bool:
        """
        Cancel an upload session and clean up chunks.

        Args:
            session_id: Upload session ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.status = UploadStatus.CANCELLED
        session.updated_at = time.time()

        self._cleanup_chunks(session_id)

        return True

    def check_duplicate(self, file_hash: str) -> Optional[str]:
        """
        Check if a file with the given hash already exists.

        Args:
            file_hash: SHA-256 hash of the file

        Returns:
            Asset ID if duplicate exists, None otherwise
        """
        return self.dedupe_index.get(file_hash)

    def get_asset_path(self, asset_id: str) -> Optional[Path]:
        """
        Get the file path for an asset.

        Args:
            asset_id: Asset ID

        Returns:
            Path to asset file if it exists, None otherwise
        """
        asset_path = self.storage_path / "assets" / asset_id
        return asset_path if asset_path.exists() else None

    def _generate_session_id(self, file_name: str, file_size: int) -> str:
        """Generate unique session ID."""
        data = f"{file_name}_{file_size}_{time.time()}".encode('utf-8')
        return hashlib.sha256(data).hexdigest()[:16]

    def _generate_asset_id(self, file_hash: str) -> str:
        """Generate asset ID from file hash."""
        return file_hash[:16]

    def _get_chunk_path(self, session_id: str, chunk_index: int) -> Path:
        """Get path for a chunk file."""
        return self.storage_path / session_id / "chunks" / f"chunk_{chunk_index:06d}"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _cleanup_chunks(self, session_id: str) -> None:
        """Clean up chunk files for a session."""
        chunks_dir = self.storage_path / session_id / "chunks"
        if chunks_dir.exists():
            for chunk_file in chunks_dir.iterdir():
                chunk_file.unlink()
            chunks_dir.rmdir()

        session_dir = self.storage_path / session_id
        if session_dir.exists() and not any(session_dir.iterdir()):
            session_dir.rmdir()


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA-256 hash of a file for deduplication.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal string of SHA-256 hash
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_chunk_hash(chunk_data: bytes) -> str:
    """
    Calculate SHA-256 hash of a chunk.

    Args:
        chunk_data: Binary data of the chunk

    Returns:
        Hexadecimal string of SHA-256 hash
    """
    return hashlib.sha256(chunk_data).hexdigest()
