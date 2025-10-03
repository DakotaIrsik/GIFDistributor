"""
Tests for the upload module with resumable uploads and deduplication.
"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest

from upload import (
    UploadManager,
    UploadSession,
    UploadStatus,
    UploadChunk,
    calculate_file_hash,
    calculate_chunk_hash
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def upload_manager(temp_storage):
    """Create upload manager with temporary storage."""
    return UploadManager(storage_path=temp_storage)


@pytest.fixture
def sample_file(temp_storage):
    """Create a sample file for testing."""
    file_path = Path(temp_storage) / "test_file.txt"
    content = b"Hello, World! " * 1000  # ~14KB
    with open(file_path, 'wb') as f:
        f.write(content)
    return file_path


class TestUploadManager:
    """Test UploadManager functionality."""

    def test_initialization(self, temp_storage):
        """Test manager initialization."""
        manager = UploadManager(storage_path=temp_storage)
        assert manager.storage_path.exists()
        assert manager.chunk_size == UploadManager.DEFAULT_CHUNK_SIZE
        assert len(manager.sessions) == 0
        assert len(manager.dedupe_index) == 0

    def test_initialization_custom_chunk_size(self, temp_storage):
        """Test manager with custom chunk size."""
        chunk_size = 1024 * 1024  # 1 MB
        manager = UploadManager(storage_path=temp_storage, chunk_size=chunk_size)
        assert manager.chunk_size == chunk_size

    def test_initialization_invalid_chunk_size(self, temp_storage):
        """Test manager rejects invalid chunk sizes."""
        with pytest.raises(ValueError):
            UploadManager(storage_path=temp_storage, chunk_size=100)  # Too small

        with pytest.raises(ValueError):
            UploadManager(storage_path=temp_storage, chunk_size=200 * 1024 * 1024)  # Too large

    def test_create_session(self, upload_manager):
        """Test creating an upload session."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=10 * 1024 * 1024,  # 10 MB
            content_type="image/gif",
            metadata={"title": "Test GIF"}
        )

        assert session.file_name == "test.gif"
        assert session.file_size == 10 * 1024 * 1024
        assert session.content_type == "image/gif"
        assert session.metadata["title"] == "Test GIF"
        assert session.status == UploadStatus.PENDING
        assert session.total_chunks == 2  # 10MB / 5MB = 2 chunks
        assert len(session.chunks) == 2
        assert session.session_id in upload_manager.sessions

    def test_create_session_small_file(self, upload_manager):
        """Test session for small file (single chunk)."""
        session = upload_manager.create_session(
            file_name="small.gif",
            file_size=1024,  # 1 KB
            content_type="image/gif"
        )

        assert session.total_chunks == 1
        assert len(session.chunks) == 1
        assert session.chunks[0].chunk_size == 1024

    def test_upload_chunk(self, upload_manager):
        """Test uploading a chunk."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        chunk_data = b"x" * 1024
        success, error = upload_manager.upload_chunk(
            session_id=session.session_id,
            chunk_index=0,
            chunk_data=chunk_data
        )

        assert success is True
        assert error is None
        assert session.chunks[0].uploaded is True
        assert session.chunks[0].chunk_hash == calculate_chunk_hash(chunk_data)
        assert session.status == UploadStatus.IN_PROGRESS

    def test_upload_chunk_invalid_session(self, upload_manager):
        """Test uploading chunk with invalid session."""
        success, error = upload_manager.upload_chunk(
            session_id="invalid",
            chunk_index=0,
            chunk_data=b"data"
        )

        assert success is False
        assert error == "Session not found"

    def test_upload_chunk_invalid_index(self, upload_manager):
        """Test uploading chunk with invalid index."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        success, error = upload_manager.upload_chunk(
            session_id=session.session_id,
            chunk_index=999,
            chunk_data=b"data"
        )

        assert success is False
        assert "Invalid chunk index" in error

    def test_upload_chunk_size_mismatch(self, upload_manager):
        """Test uploading chunk with wrong size."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        success, error = upload_manager.upload_chunk(
            session_id=session.session_id,
            chunk_index=0,
            chunk_data=b"wrong size"
        )

        assert success is False
        assert "Chunk size mismatch" in error

    def test_complete_upload_flow(self, upload_manager):
        """Test complete upload flow with multiple chunks."""
        # Create session for 2-chunk file
        file_size = 10 * 1024 * 1024  # 10 MB
        chunk_size = 5 * 1024 * 1024   # 5 MB
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=file_size,
            content_type="image/gif"
        )

        # Upload both chunks
        chunk1_data = b"a" * chunk_size
        chunk2_data = b"b" * chunk_size

        success, error = upload_manager.upload_chunk(session.session_id, 0, chunk1_data)
        assert success is True

        success, error = upload_manager.upload_chunk(session.session_id, 1, chunk2_data)
        assert success is True

        # Finalize upload
        success, error, asset_id = upload_manager.finalize_upload(session.session_id)

        assert success is True
        assert error is None
        assert asset_id is not None
        assert session.status == UploadStatus.COMPLETED
        assert session.file_hash is not None
        assert session.asset_id == asset_id

        # Verify asset file exists
        asset_path = upload_manager.get_asset_path(asset_id)
        assert asset_path is not None
        assert asset_path.exists()

    def test_finalize_upload_incomplete(self, upload_manager):
        """Test finalizing incomplete upload."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=10 * 1024 * 1024,
            content_type="image/gif"
        )

        # Upload only first chunk
        chunk_data = b"x" * (5 * 1024 * 1024)
        upload_manager.upload_chunk(session.session_id, 0, chunk_data)

        # Try to finalize
        success, error, asset_id = upload_manager.finalize_upload(session.session_id)

        assert success is False
        assert "Upload incomplete" in error
        assert asset_id is None

    def test_deduplication(self, upload_manager):
        """Test file deduplication."""
        # Create identical content that matches expected chunk size
        chunk_data = b"identical content" * 60
        file_size = len(chunk_data)

        # Upload first file
        session1 = upload_manager.create_session(
            file_name="file1.gif",
            file_size=file_size,
            content_type="image/gif"
        )
        upload_manager.upload_chunk(session1.session_id, 0, chunk_data)
        success, error, asset_id1 = upload_manager.finalize_upload(session1.session_id)

        assert success is True

        # Upload identical file
        session2 = upload_manager.create_session(
            file_name="file2.gif",
            file_size=file_size,
            content_type="image/gif"
        )
        upload_manager.upload_chunk(session2.session_id, 0, chunk_data)
        success, error, asset_id2 = upload_manager.finalize_upload(session2.session_id)

        assert success is True
        assert asset_id1 == asset_id2  # Same asset ID for duplicate content

    def test_cancel_session(self, upload_manager):
        """Test cancelling an upload session."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        # Upload a chunk
        chunk_data = b"x" * 1024
        upload_manager.upload_chunk(session.session_id, 0, chunk_data)

        # Cancel session
        success = upload_manager.cancel_session(session.session_id)

        assert success is True
        assert session.status == UploadStatus.CANCELLED

        # Try to upload after cancellation
        success, error = upload_manager.upload_chunk(session.session_id, 0, chunk_data)
        assert success is False
        assert "Upload cancelled" in error

    def test_get_session(self, upload_manager):
        """Test retrieving a session."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        retrieved = upload_manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

        invalid = upload_manager.get_session("invalid_id")
        assert invalid is None

    def test_check_duplicate(self, upload_manager):
        """Test checking for duplicate files."""
        # Initially no duplicate
        file_hash = "abc123"
        assert upload_manager.check_duplicate(file_hash) is None

        # Add to dedupe index
        upload_manager.dedupe_index[file_hash] = "asset_123"

        # Now should find duplicate
        assert upload_manager.check_duplicate(file_hash) == "asset_123"


class TestUploadSession:
    """Test UploadSession functionality."""

    def test_get_progress_empty(self):
        """Test progress calculation for new session."""
        session = UploadSession(
            session_id="test",
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif",
            chunk_size=512,
            total_chunks=2
        )
        session.chunks = [
            UploadChunk(0, 512, "", 0),
            UploadChunk(1, 512, "", 512)
        ]

        assert session.get_progress() == 0.0

    def test_get_progress_partial(self):
        """Test progress calculation with partial upload."""
        session = UploadSession(
            session_id="test",
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif",
            chunk_size=512,
            total_chunks=2
        )
        session.chunks = [
            UploadChunk(0, 512, "hash1", 0, uploaded=True),
            UploadChunk(1, 512, "", 512)
        ]

        assert session.get_progress() == 50.0

    def test_get_progress_complete(self):
        """Test progress calculation for complete upload."""
        session = UploadSession(
            session_id="test",
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif",
            chunk_size=512,
            total_chunks=2
        )
        session.chunks = [
            UploadChunk(0, 512, "hash1", 0, uploaded=True),
            UploadChunk(1, 512, "hash2", 512, uploaded=True)
        ]

        assert session.get_progress() == 100.0

    def test_get_uploaded_bytes(self):
        """Test calculating uploaded bytes."""
        session = UploadSession(
            session_id="test",
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif",
            chunk_size=512,
            total_chunks=2
        )
        session.chunks = [
            UploadChunk(0, 512, "hash1", 0, uploaded=True),
            UploadChunk(1, 512, "", 512)
        ]

        assert session.get_uploaded_bytes() == 512

    def test_get_missing_chunks(self):
        """Test getting missing chunk indices."""
        session = UploadSession(
            session_id="test",
            file_name="test.gif",
            file_size=1536,
            content_type="image/gif",
            chunk_size=512,
            total_chunks=3
        )
        session.chunks = [
            UploadChunk(0, 512, "hash1", 0, uploaded=True),
            UploadChunk(1, 512, "", 512),
            UploadChunk(2, 512, "", 1024)
        ]

        missing = session.get_missing_chunks()
        assert missing == [1, 2]

    def test_is_complete(self):
        """Test checking if upload is complete."""
        session = UploadSession(
            session_id="test",
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif",
            chunk_size=512,
            total_chunks=2
        )
        session.chunks = [
            UploadChunk(0, 512, "hash1", 0, uploaded=True),
            UploadChunk(1, 512, "", 512)
        ]

        assert session.is_complete() is False

        session.chunks[1].uploaded = True
        assert session.is_complete() is True


class TestUtilityFunctions:
    """Test utility functions."""

    def test_calculate_file_hash(self, sample_file):
        """Test file hash calculation."""
        hash1 = calculate_file_hash(str(sample_file))
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters
        assert hash1 == calculate_file_hash(str(sample_file))  # Consistent

    def test_calculate_chunk_hash(self):
        """Test chunk hash calculation."""
        data = b"test data"
        hash1 = calculate_chunk_hash(data)
        assert len(hash1) == 64  # SHA-256
        assert hash1 == calculate_chunk_hash(data)  # Consistent

        # Different data produces different hash
        hash2 = calculate_chunk_hash(b"different data")
        assert hash1 != hash2


class TestResumableUpload:
    """Test resumable upload scenarios."""

    def test_resume_after_interruption(self, upload_manager):
        """Test resuming upload after interruption."""
        # Create session with large enough file for 2 chunks
        file_size = 10 * 1024 * 1024  # 10 MB
        chunk_size = upload_manager.chunk_size  # 5 MB

        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=file_size,
            content_type="image/gif"
        )

        chunk1 = b"a" * chunk_size
        upload_manager.upload_chunk(session.session_id, 0, chunk1)

        # Simulate interruption - get session again
        resumed_session = upload_manager.get_session(session.session_id)
        assert resumed_session is not None
        assert resumed_session.get_progress() == 50.0
        assert resumed_session.get_missing_chunks() == [1]

        # Resume with second chunk
        chunk2 = b"b" * chunk_size
        upload_manager.upload_chunk(session.session_id, 1, chunk2)

        # Finalize
        success, error, asset_id = upload_manager.finalize_upload(session.session_id)
        assert success is True
        assert asset_id is not None

    def test_upload_chunks_out_of_order(self, upload_manager):
        """Test uploading chunks out of order."""
        # Create session with 3 chunks (15 MB = 3 chunks of 5 MB each)
        file_size = 15 * 1024 * 1024
        chunk_size = upload_manager.chunk_size

        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=file_size,
            content_type="image/gif"
        )

        chunk1 = b"a" * chunk_size
        chunk2 = b"b" * chunk_size
        chunk3 = b"c" * chunk_size

        # Upload in reverse order
        upload_manager.upload_chunk(session.session_id, 2, chunk3)
        upload_manager.upload_chunk(session.session_id, 0, chunk1)
        upload_manager.upload_chunk(session.session_id, 1, chunk2)

        # Should still finalize correctly
        success, error, asset_id = upload_manager.finalize_upload(session.session_id)
        assert success is True

    def test_duplicate_chunk_upload(self, upload_manager):
        """Test uploading the same chunk twice."""
        session = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        chunk_data = b"x" * 1024

        # Upload chunk
        success1, error1 = upload_manager.upload_chunk(session.session_id, 0, chunk_data)
        assert success1 is True

        # Upload same chunk again
        success2, error2 = upload_manager.upload_chunk(session.session_id, 0, chunk_data)
        assert success2 is True  # Should succeed (idempotent)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_file(self, upload_manager):
        """Test handling empty file."""
        with pytest.raises(ValueError, match="File size must be greater than 0"):
            # Empty file should raise ValueError
            session = upload_manager.create_session(
                file_name="empty.gif",
                file_size=0,
                content_type="image/gif"
            )

    def test_very_large_file(self, upload_manager):
        """Test session creation for very large file."""
        # 5 GB file
        large_file_size = 5 * 1024 * 1024 * 1024
        session = upload_manager.create_session(
            file_name="large.gif",
            file_size=large_file_size,
            content_type="image/gif"
        )

        expected_chunks = (large_file_size + upload_manager.chunk_size - 1) // upload_manager.chunk_size
        assert session.total_chunks == expected_chunks
        assert len(session.chunks) == expected_chunks

    def test_session_id_uniqueness(self, upload_manager):
        """Test that session IDs are unique."""
        session1 = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        session2 = upload_manager.create_session(
            file_name="test.gif",
            file_size=1024,
            content_type="image/gif"
        )

        assert session1.session_id != session2.session_id

    def test_finalize_nonexistent_session(self, upload_manager):
        """Test finalizing nonexistent session."""
        success, error, asset_id = upload_manager.finalize_upload("nonexistent")
        assert success is False
        assert error == "Session not found"
        assert asset_id is None

    def test_cancel_nonexistent_session(self, upload_manager):
        """Test cancelling nonexistent session."""
        success = upload_manager.cancel_session("nonexistent")
        assert success is False
