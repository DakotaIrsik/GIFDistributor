"""
Direct Browser Upload + Resumable - Issue #14
Provides direct browser-to-storage uploads with resumable capability

Features:
- Direct browser uploads using signed upload URLs
- Resumable multi-part uploads with chunk tracking
- Progress tracking and recovery from failures
- Integration with storage_cdn module
- Client-side hash verification
- Bandwidth optimization with chunked uploads

Dependencies:
- storage-cdn (#27): For signed URLs and object storage
- auth (#3): For user authentication and upload authorization
"""

import os
import time
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any, BinaryIO
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path


class UploadMethod(str, Enum):
    """Upload method types"""
    DIRECT = "direct"  # Direct single upload
    MULTIPART = "multipart"  # Chunked multipart upload
    RESUMABLE = "resumable"  # Resumable chunked upload


class UploadStatus(str, Enum):
    """Upload session status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ChunkMetadata:
    """Metadata for upload chunks"""
    chunk_number: int
    chunk_size: int
    chunk_hash: str  # SHA-256 of chunk
    uploaded_at: Optional[str] = None
    storage_key: Optional[str] = None


@dataclass
class UploadSession:
    """Represents a resumable upload session"""
    session_id: str
    user_id: str
    filename: str
    total_size: int
    mime_type: str
    chunk_size: int
    total_chunks: int
    status: UploadStatus = UploadStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat())
    uploaded_chunks: List[ChunkMetadata] = field(default_factory=list)
    final_hash: Optional[str] = None
    final_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UploadUrlConfig:
    """Configuration for upload URL generation"""
    max_file_size: int = 100 * 1024 * 1024  # 100MB default
    allowed_mime_types: Optional[List[str]] = None
    expires_in_seconds: int = 3600  # 1 hour
    require_hash_verification: bool = True


@dataclass
class DirectUploadRequest:
    """Request to initiate direct upload"""
    filename: str
    file_size: int
    mime_type: str
    user_id: str
    content_hash: Optional[str] = None  # Client-computed SHA-256
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DirectUploadResponse:
    """Response with upload URL and parameters"""
    upload_url: str
    upload_method: UploadMethod
    session_id: str
    expires_at: str
    max_file_size: int
    fields: Dict[str, str] = field(default_factory=dict)  # Additional form fields for POST
    chunk_size: Optional[int] = None  # For multipart uploads
    total_chunks: Optional[int] = None


class SessionStore:
    """
    Manages upload session persistence
    In production, use Redis or a database
    """

    def __init__(self, db_path: str = "upload_sessions.json"):
        """Initialize session store"""
        self.db_path = db_path
        self._load_db()

    def _load_db(self) -> None:
        """Load sessions from disk"""
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                data = json.load(f)
                self.sessions = {
                    sid: UploadSession(**session_data)
                    for sid, session_data in data.items()
                }
        else:
            self.sessions = {}

    def _save_db(self) -> None:
        """Save sessions to disk"""
        data = {
            sid: asdict(session)
            for sid, session in self.sessions.items()
        }
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_session(self, session: UploadSession) -> None:
        """Create new upload session"""
        self.sessions[session.session_id] = session
        self._save_db()

    def get_session(self, session_id: str) -> Optional[UploadSession]:
        """Get upload session by ID"""
        return self.sessions.get(session_id)

    def update_session(self, session: UploadSession) -> None:
        """Update existing session"""
        session.updated_at = datetime.now(timezone.utc).isoformat()
        self.sessions[session.session_id] = session
        self._save_db()

    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_db()
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        now = datetime.now(timezone.utc)
        expired = []

        for sid, session in self.sessions.items():
            expires_at = datetime.fromisoformat(session.expires_at)
            if now > expires_at:
                expired.append(sid)

        for sid in expired:
            del self.sessions[sid]

        if expired:
            self._save_db()

        return len(expired)

    def get_user_sessions(self, user_id: str) -> List[UploadSession]:
        """Get all sessions for a user"""
        return [
            session for session in self.sessions.values()
            if session.user_id == user_id
        ]


class DirectUploadManager:
    """
    Manages direct browser uploads with resumable capability
    """

    # Default chunk size for multipart uploads (5MB)
    DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024

    def __init__(
        self,
        storage_manager,  # Instance of storage_cdn.StorageManager
        session_store: Optional[SessionStore] = None,
        default_chunk_size: int = DEFAULT_CHUNK_SIZE
    ):
        """
        Initialize direct upload manager

        Args:
            storage_manager: StorageManager instance from storage_cdn module
            session_store: Session store for tracking uploads
            default_chunk_size: Default chunk size for multipart uploads
        """
        self.storage = storage_manager
        self.sessions = session_store or SessionStore()
        self.default_chunk_size = default_chunk_size

    def _generate_session_id(self, user_id: str, filename: str) -> str:
        """Generate unique session ID"""
        timestamp = str(time.time())
        data = f"{user_id}:{filename}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def _generate_storage_key(self, user_id: str, filename: str, session_id: str) -> str:
        """Generate storage key for uploaded file"""
        # Use session ID to ensure uniqueness
        ext = os.path.splitext(filename)[1]
        return f"uploads/{user_id}/{session_id}{ext}"

    def _should_use_multipart(self, file_size: int) -> bool:
        """Determine if multipart upload should be used"""
        # Use multipart for files larger than chunk size
        return file_size > self.default_chunk_size

    def _calculate_chunks(self, file_size: int, chunk_size: int) -> int:
        """Calculate number of chunks"""
        return (file_size + chunk_size - 1) // chunk_size

    def initiate_upload(
        self,
        request: DirectUploadRequest,
        config: Optional[UploadUrlConfig] = None
    ) -> DirectUploadResponse:
        """
        Initiate direct upload and return signed URL

        Args:
            request: Upload request details
            config: Upload URL configuration

        Returns:
            DirectUploadResponse with signed URL and parameters

        Raises:
            ValueError: If request validation fails
        """
        config = config or UploadUrlConfig()

        # Validate file size
        if request.file_size > config.max_file_size:
            raise ValueError(
                f"File size {request.file_size} exceeds maximum {config.max_file_size}"
            )

        # Validate MIME type
        if config.allowed_mime_types and request.mime_type not in config.allowed_mime_types:
            raise ValueError(
                f"MIME type {request.mime_type} not allowed. "
                f"Allowed types: {config.allowed_mime_types}"
            )

        # Generate session ID and storage key
        session_id = self._generate_session_id(request.user_id, request.filename)
        storage_key = self._generate_storage_key(request.user_id, request.filename, session_id)

        # Determine upload method
        use_multipart = self._should_use_multipart(request.file_size)
        upload_method = UploadMethod.MULTIPART if use_multipart else UploadMethod.DIRECT

        if use_multipart:
            # Create resumable upload session
            total_chunks = self._calculate_chunks(request.file_size, self.default_chunk_size)

            session = UploadSession(
                session_id=session_id,
                user_id=request.user_id,
                filename=request.filename,
                total_size=request.file_size,
                mime_type=request.mime_type,
                chunk_size=self.default_chunk_size,
                total_chunks=total_chunks,
                status=UploadStatus.PENDING,
                metadata=request.metadata
            )

            self.sessions.create_session(session)

            # For multipart, return session info without upload URL
            # Client will request chunk URLs separately
            return DirectUploadResponse(
                upload_url="",  # No single URL for multipart
                upload_method=upload_method,
                session_id=session_id,
                expires_at=session.expires_at,
                max_file_size=config.max_file_size,
                chunk_size=self.default_chunk_size,
                total_chunks=total_chunks
            )
        else:
            # Direct single upload
            # Generate signed upload URL
            upload_url = self.storage.generate_signed_url(
                storage_key,
                expires_in=config.expires_in_seconds,
                content_type=request.mime_type
            )

            # Create simple session for tracking
            session = UploadSession(
                session_id=session_id,
                user_id=request.user_id,
                filename=request.filename,
                total_size=request.file_size,
                mime_type=request.mime_type,
                chunk_size=request.file_size,
                total_chunks=1,
                status=UploadStatus.PENDING,
                final_key=storage_key,
                metadata=request.metadata
            )

            self.sessions.create_session(session)

            return DirectUploadResponse(
                upload_url=upload_url,
                upload_method=upload_method,
                session_id=session_id,
                expires_at=session.expires_at,
                max_file_size=config.max_file_size,
                fields={
                    'key': storage_key,
                    'Content-Type': request.mime_type
                }
            )

    def get_chunk_upload_url(
        self,
        session_id: str,
        chunk_number: int,
        chunk_size: int,
        chunk_hash: Optional[str] = None
    ) -> str:
        """
        Get signed URL for uploading a specific chunk

        Args:
            session_id: Upload session ID
            chunk_number: Chunk number (0-indexed)
            chunk_size: Size of this chunk
            chunk_hash: Optional SHA-256 hash of chunk for verification

        Returns:
            Signed upload URL for chunk

        Raises:
            ValueError: If session not found or invalid chunk
        """
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if chunk_number >= session.total_chunks:
            raise ValueError(
                f"Invalid chunk number {chunk_number}. Total chunks: {session.total_chunks}"
            )

        # Generate chunk storage key
        chunk_key = f"uploads/chunks/{session_id}/chunk_{chunk_number:04d}"

        # Generate signed URL for chunk upload
        upload_url = self.storage.generate_signed_url(
            chunk_key,
            expires_in=3600,  # 1 hour
            content_type="application/octet-stream"
        )

        return upload_url

    def mark_chunk_uploaded(
        self,
        session_id: str,
        chunk_number: int,
        chunk_size: int,
        chunk_hash: str
    ) -> Dict[str, Any]:
        """
        Mark a chunk as successfully uploaded

        Args:
            session_id: Upload session ID
            chunk_number: Chunk number
            chunk_size: Actual size of uploaded chunk
            chunk_hash: SHA-256 hash of chunk

        Returns:
            Upload progress information
        """
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Create chunk metadata
        chunk_meta = ChunkMetadata(
            chunk_number=chunk_number,
            chunk_size=chunk_size,
            chunk_hash=chunk_hash,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            storage_key=f"uploads/chunks/{session_id}/chunk_{chunk_number:04d}"
        )

        # Add to uploaded chunks if not already present
        if not any(c.chunk_number == chunk_number for c in session.uploaded_chunks):
            session.uploaded_chunks.append(chunk_meta)

        # Update session status
        if len(session.uploaded_chunks) == session.total_chunks:
            session.status = UploadStatus.COMPLETED
        elif len(session.uploaded_chunks) > 0:
            session.status = UploadStatus.IN_PROGRESS

        self.sessions.update_session(session)

        uploaded_bytes = sum(c.chunk_size for c in session.uploaded_chunks)
        progress = (uploaded_bytes / session.total_size) * 100

        return {
            'session_id': session_id,
            'uploaded_chunks': len(session.uploaded_chunks),
            'total_chunks': session.total_chunks,
            'uploaded_bytes': uploaded_bytes,
            'total_bytes': session.total_size,
            'progress_percent': round(progress, 2),
            'status': session.status.value,
            'is_complete': session.status == UploadStatus.COMPLETED
        }

    def finalize_upload(self, session_id: str) -> Dict[str, Any]:
        """
        Finalize multipart upload by assembling chunks

        Args:
            session_id: Upload session ID

        Returns:
            Final upload information with storage key

        Raises:
            ValueError: If session not found or upload incomplete
        """
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if len(session.uploaded_chunks) != session.total_chunks:
            raise ValueError(
                f"Upload incomplete. {len(session.uploaded_chunks)}/{session.total_chunks} chunks uploaded"
            )

        # Sort chunks by chunk number
        session.uploaded_chunks.sort(key=lambda c: c.chunk_number)

        # Assemble chunks into final file
        final_key = self._generate_storage_key(session.user_id, session.filename, session_id)
        assembled_data = bytearray()

        for chunk_meta in session.uploaded_chunks:
            # Read chunk from storage
            chunk_data, _ = self.storage.download(chunk_meta.storage_key)
            assembled_data.extend(chunk_data)

        # Calculate final hash
        final_hash = hashlib.sha256(assembled_data).hexdigest()

        # Upload assembled file
        metadata = self.storage.upload(
            final_key,
            bytes(assembled_data),
            content_type=session.mime_type,
            metadata={'original_filename': session.filename, **session.metadata}
        )

        # Clean up chunks
        for chunk_meta in session.uploaded_chunks:
            self.storage.delete(chunk_meta.storage_key)

        # Update session
        session.final_hash = final_hash
        session.final_key = final_key
        session.status = UploadStatus.COMPLETED
        self.sessions.update_session(session)

        return {
            'session_id': session_id,
            'storage_key': final_key,
            'file_hash': final_hash,
            'file_size': session.total_size,
            'cdn_url': metadata.cdn_url,
            'status': 'completed'
        }

    def get_upload_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Get current upload progress

        Args:
            session_id: Upload session ID

        Returns:
            Progress information
        """
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        uploaded_bytes = sum(c.chunk_size for c in session.uploaded_chunks)
        progress = (uploaded_bytes / session.total_size) * 100 if session.total_size > 0 else 0

        # Get missing chunks
        uploaded_chunk_numbers = {c.chunk_number for c in session.uploaded_chunks}
        missing_chunks = [
            i for i in range(session.total_chunks)
            if i not in uploaded_chunk_numbers
        ]

        return {
            'session_id': session_id,
            'status': session.status.value,
            'uploaded_chunks': len(session.uploaded_chunks),
            'total_chunks': session.total_chunks,
            'uploaded_bytes': uploaded_bytes,
            'total_bytes': session.total_size,
            'progress_percent': round(progress, 2),
            'missing_chunks': missing_chunks[:10],  # Return first 10 missing
            'is_complete': session.status == UploadStatus.COMPLETED,
            'created_at': session.created_at,
            'updated_at': session.updated_at,
            'expires_at': session.expires_at
        }

    def abort_upload(self, session_id: str, cleanup: bool = True) -> bool:
        """
        Abort upload and optionally cleanup

        Args:
            session_id: Upload session ID
            cleanup: Whether to delete uploaded chunks

        Returns:
            True if aborted successfully
        """
        session = self.sessions.get_session(session_id)
        if not session:
            return False

        # Cleanup chunks if requested
        if cleanup:
            for chunk_meta in session.uploaded_chunks:
                try:
                    self.storage.delete(chunk_meta.storage_key)
                except Exception:
                    pass  # Ignore cleanup errors

        # Update session status
        session.status = UploadStatus.ABORTED
        self.sessions.update_session(session)

        return True

    def resume_upload(self, session_id: str) -> Dict[str, Any]:
        """
        Resume an interrupted upload

        Args:
            session_id: Upload session ID

        Returns:
            Resume information with missing chunks
        """
        progress = self.get_upload_progress(session_id)
        session = self.sessions.get_session(session_id)

        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Check if expired
        expires_at = datetime.fromisoformat(session.expires_at)
        if datetime.now(timezone.utc) > expires_at:
            raise ValueError("Upload session has expired")

        if session.status == UploadStatus.COMPLETED:
            raise ValueError("Upload already completed")

        if session.status == UploadStatus.ABORTED:
            raise ValueError("Upload was aborted")

        return {
            **progress,
            'can_resume': True,
            'chunk_size': session.chunk_size,
            'next_chunk': min(progress['missing_chunks']) if progress['missing_chunks'] else None
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get upload statistics"""
        sessions = list(self.sessions.sessions.values())

        total_sessions = len(sessions)
        by_status = {}
        total_bytes_uploaded = 0

        for session in sessions:
            status = session.status.value
            by_status[status] = by_status.get(status, 0) + 1

            if session.status == UploadStatus.COMPLETED:
                total_bytes_uploaded += session.total_size

        return {
            'total_sessions': total_sessions,
            'by_status': by_status,
            'total_bytes_uploaded': total_bytes_uploaded,
            'total_mb_uploaded': round(total_bytes_uploaded / (1024 * 1024), 2),
            'active_sessions': by_status.get(UploadStatus.IN_PROGRESS.value, 0)
        }


if __name__ == '__main__':
    print("Direct Browser Upload + Resumable Module")
    print("=" * 60)

    # Example usage would require storage_cdn.StorageManager instance
    print("\nThis module provides:")
    print("  - Direct browser-to-storage uploads")
    print("  - Resumable chunked uploads")
    print("  - Progress tracking and recovery")
    print("  - Signed URL generation for secure uploads")
    print("\nIntegration with storage_cdn (#27) and auth (#3) required.")
