"""
Upload Module - Issue #15
Direct, resumable uploads + deduplication

Features:
- Content-based deduplication using SHA-256 hashing
- Chunk-based hashing for large files
- Upload tracking and metadata management
- Duplicate detection before upload completion
- Storage space optimization
"""

import os
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple, Any, BinaryIO
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum


class UploadStatus(str, Enum):
    """Upload status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


@dataclass
class FileMetadata:
    """Metadata for uploaded files"""
    file_hash: str
    filename: str
    size_bytes: int
    mime_type: str
    upload_time: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    storage_path: Optional[str] = None


@dataclass
class UploadSession:
    """Represents an upload session"""
    session_id: str
    file_hash: str
    filename: str
    total_size: int
    uploaded_bytes: int = 0
    status: UploadStatus = UploadStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    chunks_received: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileHasher:
    """Utilities for file hashing and deduplication"""

    @staticmethod
    def hash_file(file_path: str, chunk_size: int = 8192) -> str:
        """
        Generate SHA-256 hash of file contents

        Args:
            file_path: Path to file
            chunk_size: Size of chunks to read (default 8KB)

        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """
        Generate SHA-256 hash of byte data

        Args:
            data: Byte data to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_stream(stream: BinaryIO, chunk_size: int = 8192) -> str:
        """
        Generate SHA-256 hash of stream

        Args:
            stream: Binary stream to hash
            chunk_size: Size of chunks to read

        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()

        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def quick_hash(file_path: str, sample_size: int = 1024 * 1024) -> str:
        """
        Generate quick hash using file header, footer, and size
        Useful for fast duplicate detection before full hash

        Args:
            file_path: Path to file
            sample_size: Size of header/footer samples (default 1MB)

        Returns:
            Hexadecimal hash string
        """
        file_size = os.path.getsize(file_path)
        sha256 = hashlib.sha256()

        # Include file size in hash
        sha256.update(str(file_size).encode())

        with open(file_path, 'rb') as f:
            # Hash header
            header = f.read(min(sample_size, file_size))
            sha256.update(header)

            # Hash footer if file is large enough
            if file_size > sample_size * 2:
                f.seek(-sample_size, os.SEEK_END)
                footer = f.read(sample_size)
                sha256.update(footer)

        return sha256.hexdigest()


class DeduplicationStore:
    """
    Manages file deduplication database
    In production, this would use a real database (PostgreSQL, Redis, etc.)
    """

    def __init__(self, db_path: str = "dedupe.json"):
        """
        Initialize deduplication store

        Args:
            db_path: Path to JSON database file
        """
        self.db_path = db_path
        self._load_db()

    def _load_db(self) -> None:
        """Load database from disk"""
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {
                'files': {},  # hash -> FileMetadata
                'uploads': {},  # session_id -> UploadSession
            }

    def _save_db(self) -> None:
        """Save database to disk"""
        with open(self.db_path, 'w') as f:
            json.dump(self.db, f, indent=2)

    def is_duplicate(self, file_hash: str) -> bool:
        """
        Check if file hash already exists

        Args:
            file_hash: SHA-256 hash of file

        Returns:
            True if duplicate exists
        """
        return file_hash in self.db['files']

    def get_file_metadata(self, file_hash: str) -> Optional[FileMetadata]:
        """
        Get metadata for existing file

        Args:
            file_hash: SHA-256 hash of file

        Returns:
            FileMetadata if exists, None otherwise
        """
        if file_hash in self.db['files']:
            return FileMetadata(**self.db['files'][file_hash])
        return None

    def add_file(self, metadata: FileMetadata) -> None:
        """
        Add file metadata to store

        Args:
            metadata: File metadata to store
        """
        self.db['files'][metadata.file_hash] = asdict(metadata)
        self._save_db()

    def remove_file(self, file_hash: str) -> bool:
        """
        Remove file from store

        Args:
            file_hash: Hash of file to remove

        Returns:
            True if file was removed, False if not found
        """
        if file_hash in self.db['files']:
            del self.db['files'][file_hash]
            self._save_db()
            return True
        return False

    def get_all_files(self) -> List[FileMetadata]:
        """Get all file metadata"""
        return [FileMetadata(**data) for data in self.db['files'].values()]

    def get_user_files(self, user_id: str) -> List[FileMetadata]:
        """Get all files for a specific user"""
        return [
            FileMetadata(**data)
            for data in self.db['files'].values()
            if data.get('user_id') == user_id
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        files = list(self.db['files'].values())
        total_size = sum(f['size_bytes'] for f in files)
        total_files = len(files)

        users = set(f.get('user_id') for f in files if f.get('user_id'))

        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'unique_users': len(users),
            'avg_file_size_mb': round(total_size / total_files / (1024 * 1024), 2) if total_files > 0 else 0
        }


class UploadManager:
    """
    Manages file uploads with deduplication
    """

    def __init__(self, storage_dir: str = "uploads", dedupe_store: Optional[DeduplicationStore] = None):
        """
        Initialize upload manager

        Args:
            storage_dir: Directory to store uploaded files
            dedupe_store: Deduplication store instance
        """
        self.storage_dir = storage_dir
        self.dedupe_store = dedupe_store or DeduplicationStore()
        os.makedirs(storage_dir, exist_ok=True)

    def check_duplicate(self, file_path: str) -> Tuple[bool, Optional[FileMetadata]]:
        """
        Check if file is a duplicate

        Args:
            file_path: Path to file to check

        Returns:
            Tuple of (is_duplicate, existing_metadata)
        """
        file_hash = FileHasher.hash_file(file_path)
        existing = self.dedupe_store.get_file_metadata(file_hash)

        if existing:
            return (True, existing)
        return (False, None)

    def upload_file(
        self,
        file_path: str,
        filename: Optional[str] = None,
        mime_type: str = "application/octet-stream",
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        skip_duplicate_check: bool = False
    ) -> Tuple[bool, str, Optional[FileMetadata]]:
        """
        Upload a file with deduplication

        Args:
            file_path: Path to file to upload
            filename: Original filename (uses basename if not provided)
            mime_type: MIME type of file
            user_id: User ID uploading the file
            title: Title for the file
            tags: List of tags
            description: File description
            skip_duplicate_check: Skip duplicate checking (for testing)

        Returns:
            Tuple of (success, message, metadata)
        """
        if not os.path.exists(file_path):
            return (False, f"File not found: {file_path}", None)

        # Calculate hash
        file_hash = FileHasher.hash_file(file_path)
        file_size = os.path.getsize(file_path)

        if not filename:
            filename = os.path.basename(file_path)

        # Check for duplicates
        if not skip_duplicate_check:
            existing = self.dedupe_store.get_file_metadata(file_hash)
            if existing:
                return (
                    False,
                    f"Duplicate file detected. Original uploaded at {existing.upload_time}",
                    existing
                )

        # Copy to storage (in production, use object storage like S3)
        storage_path = os.path.join(self.storage_dir, file_hash[:2], file_hash[2:4], file_hash)
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        # Copy file
        import shutil
        shutil.copy2(file_path, storage_path)

        # Create metadata
        metadata = FileMetadata(
            file_hash=file_hash,
            filename=filename,
            size_bytes=file_size,
            mime_type=mime_type,
            upload_time=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            title=title or filename,
            tags=tags or [],
            description=description,
            storage_path=storage_path
        )

        # Store metadata
        self.dedupe_store.add_file(metadata)

        return (True, f"File uploaded successfully: {file_hash}", metadata)

    def get_file_path(self, file_hash: str) -> Optional[str]:
        """
        Get storage path for a file by hash

        Args:
            file_hash: SHA-256 hash of file

        Returns:
            Storage path if exists, None otherwise
        """
        metadata = self.dedupe_store.get_file_metadata(file_hash)
        if metadata and metadata.storage_path:
            if os.path.exists(metadata.storage_path):
                return metadata.storage_path
        return None

    def delete_file(self, file_hash: str, remove_from_disk: bool = True) -> bool:
        """
        Delete file from storage

        Args:
            file_hash: Hash of file to delete
            remove_from_disk: Whether to remove physical file

        Returns:
            True if deleted, False if not found
        """
        metadata = self.dedupe_store.get_file_metadata(file_hash)

        if not metadata:
            return False

        # Remove from disk
        if remove_from_disk and metadata.storage_path:
            if os.path.exists(metadata.storage_path):
                os.remove(metadata.storage_path)

        # Remove from database
        return self.dedupe_store.remove_file(file_hash)

    def get_stats(self) -> Dict[str, Any]:
        """Get upload statistics"""
        return self.dedupe_store.get_stats()


# Convenience functions

def hash_file(file_path: str) -> str:
    """Quick helper to hash a file"""
    return FileHasher.hash_file(file_path)


def check_duplicate(file_path: str, dedupe_store: Optional[DeduplicationStore] = None) -> Tuple[bool, Optional[str]]:
    """
    Quick helper to check if file is duplicate

    Args:
        file_path: Path to file
        dedupe_store: Optional deduplication store

    Returns:
        Tuple of (is_duplicate, existing_hash)
    """
    store = dedupe_store or DeduplicationStore()
    file_hash = FileHasher.hash_file(file_path)
    is_dup = store.is_duplicate(file_hash)
    return (is_dup, file_hash if is_dup else None)


if __name__ == '__main__':
    # Example usage
    print("Upload Module - File Deduplication System")
    print("=" * 60)

    # Create upload manager
    manager = UploadManager(storage_dir="./test_uploads")

    # Get stats
    stats = manager.get_stats()
    print(f"\nStorage Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    print(f"  Unique users: {stats['unique_users']}")
